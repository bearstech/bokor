"""\
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
B                                                                     B
B          BBBBBB     BBBBBBBB  BBk BBB  BBBBBBBB    BBBBBK           B
B          kBBBBBB  OKBBBBBBBB  BB  BBB  BBBBBBBBKO  BBRBBB           B
B          kBB  BB  BBB.  .BBB  BB BBO   BBB.  .BBB  BB  BBB          B
B          BBB BBB  BBk    .BB  BB BB    BB.    kBB  BB  .B           B
B          BBBBB    BB   O  BB  BBBB     BB  O   BB  BBOBBB           B
B           BBBBB   BBB. _ .BB  BBBB     BB. _ .BBB  BBBBK            B
B          BBB BBB  BBB,  ,BB   BB BB     BB.  ,BBB  BBBBBB           B
B          BBB  BB  BBBBBBBBB   BB kBB    BBBBBBBBB  RB  BB           B
B          BBBBBBB  BBBBBBBB    BB  BB     BBBBBBBB  BB  BB           B
B          BBBBBBB    BBBB      BBB BBB      BBBB    BB  BB           B
B                                                                     B
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software Foundation,
Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

@file feature/feature.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief process orders for bokor slave for rtorrent management
"""

import logging
import os
import signal
import subprocess
import atexit
import socket
import tempfile
import shutil
import xmlrpclib
import glob
import webbrowser

from time import sleep

from bokor.utils.tools import getfile, lastLine
from bokor.utils.hashtorrent import *

from bokor.executor.executor import Executor
from bokor.constants.error import *
from bokor.constants.system import *
from bokor.executor.executor import  aFeature, anExecutor, aPreProcess, aPostProcess
from bokor.configuration.configurable import Configurable
from bokor.interface.unsafesocket import UnsafeSocketClient
from bokor.executor.plugins.slavetorrent.rtorrent_configuration import write_conf_rtorrent
from bokor.executor.plugins.slavetorrent.constants import *
from bokor.executor.plugins.slavetorrent import bwtest as bwt
from bokor.executor.slavepost import *

from bokor.executor.plugins.slavetorrent import xmlrpc2scgi as xs

@anExecutor
class SlaveTorrent(Configurable):

    dependances = { "configuration" : [] ,
                    "interface" : [UnsafeSocketClient],
                    "transmission" : [],
                    "feature" : [SlavePost]}


    needed_configuration = { "rtorrent" :
                             {
                                 "bin": {'mandatory' : True, 'type' : 'file' , 'permission' : 'rx', 'exist' : True},

                                 "path_session": {'mandatory' : True, 'type' : 'file' , 'permission' : 'drwx', 'exist' : True},
                                 "path_dl": {'mandatory' : True, 'type' : 'file' , 'permission' : 'drwx', 'exist' : True},
                                 "path_log": {'mandatory' : True, 'type' : 'file' , 'permission' : 'drwx', 'exist' : True},

                                 "post_dl": {'mandatory' : True, 'type' : 'file' , 'permission' : 'r', 'exist' : True},

                                 "ci_up": {'mandatory' : True, 'type' : 'int'},
                                 "ci_down": {'mandatory' : True, 'type' : 'int'},

                                 "bind": {'mandatory' : True, 'type' : 'host'},
                                 "port_max": {'mandatory' : True, 'type' : 'int'},
                                 "port_min": {'mandatory' : True, 'type' : 'int'},

                                 "scgi_ip": {'mandatory' : True, 'type' : 'host'},
                                 "scgi_port": {'mandatory' : True, 'type' : 'int'},

                                 "down_kbps": {'mandatory' : True, 'type' : 'int'},
                                 "up_kbps": {'mandatory' : True, 'type' : 'int'},

                                 "max_seed": {'mandatory' : True, 'type' : 'int'},
                                 "max_leech": {'mandatory' : True, 'type' : 'int'},

                                 "max_dl_size":{'mandatory' : False, 'type' : 'int'},

                             },
                             "slave" :
                             {
                                 "url_conf" : {'mandatory' : True, 'type' : 'string'}
                             },
                         }



    return_codes = { socket.error : NO_CONNECTION_TO_RTORRENT,
                     xmlrpclib.Fault : BAD_INFO_HASH}

    def __init__(self, bokor):
        self.bokor = bokor
        self.check()
        #init some values
        #pid of rtorrent
        self.pid = None
        #process
        self.rprocess = None
        # post dl executor
        self.post = self.bokor.get_executor("SlavePost")
        #init rtorrent
        self._init_rtorrent()

        # move
        os.chdir(self.path_session)

        self.start_rtorrent()



    def _init_rtorrent(self):
        self.db = self.get('memory', 'sqlitedir', '/tmp')  + '/' + 'post.db'
        # we keep pathes and make sure they have a final /:
        self.path_session = self.get("rtorrent", "path_session").rstrip('/') + '/'
        self.path_dl = self.get("rtorrent", "path_dl").rstrip('/') + '/'
        self.path_log = self.get("rtorrent", "path_log").rstrip('/') + '/'
        #we keep the script post_dl
        self.post_dl = self.get("rtorrent", "post_dl")

        # get bin
        self.bin = self.get("rtorrent", "bin")
        # get rtorrentrc (in path_session)
        self.rtorrentrc = self.path_session + "/rtorrent.rc"

        #max_size_dl : -1 if none
        self.max_dl_size = int(self.get("rtorrent", "max_dl_size", -1))
        
        # get command to launch rtorrent
        self.rtorrent_cmd = [self.bin, '-n', '-o', 'import=%s' %
                         self.rtorrentrc]

        self.host = 'scgi://%s:%s' % (
            self.get("rtorrent", "scgi_ip"),
            self.get("rtorrent", "scgi_port"))
        #get link to rtorrent
        self.rtc = xs.RTorrentXMLRPCClient(self.host)



        self.rtorrent_conf = write_conf_rtorrent(
            self.rtorrentrc,
            self.db,
            self.get("rtorrent", "ci_up"),
            self.get("rtorrent", "ci_down"), self.bokor.token,
            self.get("rtorrent", "bind"),
            self.get("rtorrent", "port_max"),
            self.get("rtorrent", "port_min"),
            self.get("rtorrent", "scgi_ip"),
            self.get("rtorrent", "scgi_port"),
            self.path_session, self.path_dl, self.path_log,
            self.post_dl,
            self.get("rtorrent", "down_kbps"),
            self.get("rtorrent", "up_kbps"),
            self.get("rtorrent", "max_seed"),
            self.get("rtorrent", "max_leech"),
        )


#------------------------------------------------------------------------------
# Rtorrent software management
    @aFeature
    def get_rtorrent_conf(self):
        """Get conf file content of rtorrent as memorised by SlaveTorrent know
        it

        @return s string of the Conf"""

        return self.rtorrent_conf

    @aFeature
    def status_rtorrent(self):
        """Request Rtorrent status

        @return: Bool; True if rtorrent running
        """
        if not self.pid :
            return False
        else :
            #FIXME can be false
            return True



    @aFeature
    def rmlock(self):
        """rm rtorrent lock file

        @return: True
        """        
        os.remove(self.path_session + "/rtorrent.lock")
        return True


    @aFeature
    def stop_rtorrent(self):
        """Stop rtorrent

        @return: True
        """
        if OS.startswith('CYGWIN'):
            subprocess.Popen(["taskkill.exe", "/F", "/IM", "rtorrent.exe"])
            self.rmlock()
        else:
            if self.pid :
                os.kill(self.pid, signal.SIGTERM)
        self.pid = None
        print 'RTORRENT IS STOPPED'
        logging.info('RTORRENT IS STOPPED')
        return True

    @aFeature
    def start_rtorrent(self) :
        """Launch Rtorrent

        @return: Rtorrent pid
        """
        if self.pid:
            return self.pid

        self.rprocess = subprocess.Popen(self.rtorrent_cmd)
        self.pid = self.rprocess.pid
        atexit.register(self.stop_rtorrent)
        # rtorrent need to be ready, so we wait a little
        sleep(0.5)
        print 'RTORRENT IS STARTED'
        logging.info('RTORRENT IS STARTED')
        return self.pid

#------------------------------------------------------------------------------
# Rtorrent system function :



    @aFeature
    def version(self) :
        """Rtorrent version

        @return: Rtorrent version
        """
        return self.rtc.system.client_version()

#------------------------------------------------------------------------------
# Rtorrent download functions :


    def get_hash_files(self, hash_file):
        """Get_hash_files gives a list of hash_files given a hash file, a list
        of hash files or []

        @type  hash_file: list
        @param hash_file: list of infohashes

        @return: List of paths to torrent files
        """
        hash_files = hash_file
        if hash_files and not isinstance(hash_files, list) :
            hash_files = [hash_files]
        if not hash_files :
            hash_files = self.download_list()
        return hash_files


    @aFeature
    def download_list(self, view = ''):
        """Request the download list

        @type  view: str
        @param view: filter on download list

        @return: download list
        """
        return self.rtc.download_list('', view)

# ------ NEW DOWNLOAD ----

    @aFeature
    def create_download(self, hash_file, address_torrent, relative_path = ""):
        """Add a torrent

        @type  address_torrent: str
        @param address_torrent: URL of the torrent file

        @type  hash_file: str
        @param hash_file: Torrent infohash

        @type  relative_path: str
        @param relative_path: Final path for download

        @return: True or None (False ??)
        """

        logging.info("adding %s from %s (relative path : %s)" % (hash_file,
                                                                 address_torrent, relative_path))
        rp = None;
        # is the hash_file already known ?
        if hash_file in self.rtc.download_list():
            if relative_path:
                completes = [ dl['hash_file'] for dl in self.status_view('complete')]
                status = 'todo'
                if hash_file not in completes :
                    status = 'downloading'
                self.post.create_relative_path_if_needed(hash_file, relative_path, self.get_path_file(hash_file)[0], status)
            if rp :
                return rp['id']
            return 0

        tmpfile = tempfile.NamedTemporaryFile(suffix=".torrent_download")
        logging.info('Get %s.torrent' % hash_file)
        getfile(address_torrent, tmpfile.file)
        logging.info('%s.torrent fetched' % hash_file)
        print 'Create download for %s' % (hash_file)
        computeDl = getHashFromFd(tmpfile.file)
        size = getSizeFromFd(tmpfile.file)

        if not hash_file or hash_file != computeDl:
            logging.error('Error Infohash for %s' % hash_file)
            print 'Error Infohash for %s' % (hash_file)
            return "File downloaded but infohash not corresponding, %s VS %s" % (hash_file, computeDl)
        s = os.statvfs(self.path_dl)
        if self.max_dl_size > 0 : #we have a limit to respect
            freespace = self.free_dl()
        else :
            freespace = s.f_bavail * s.f_frsize
        if size >= freespace:
            self.lastError = "%s has a size of %s, but only %s remaining" % (hash_file, size, freespace)
            self._bokor_code = FREE_SPACE_ERROR
            logging.error('Error Free Space for %s' % hash_file)
            print 'Not Enough Free Space for %s' % (hash_file)
            return -1 # specific case
        dst_torrent = self.path_session + "/" + computeDl + ".torrent_download"
        shutil.copy2(tmpfile.name, dst_torrent)
        if not self.load(dst_torrent, hash_file) :
            self.lastError = "could not load %s" % (hash_file)
            self._bokor_code = LOAD_ERROR_RTORRENT
            logging.error('Error Load for %s' % hash_file)
            print 'Error Load for %s' % (hash_file)
            return 0 # error

        if relative_path:
            self.set_relative_path_for_dl(hash_file, relative_path)
        self.rtc.d.start(hash_file)
        #preapre post dl operations
        rp = self.post.create_relative_path(hash_file, relative_path, self.get_path_file(hash_file)[0], 'downloading')
        print 'Create download ended for %s' % (hash_file)
        logging.info('Create download ended for %s' % hash_file)
        return rp['id'] 



    @aFeature
    def validate_dl(self, hash_file, relative_path):
        """validate the relative_path of  a new torrent

        @type  request: dict
        @param request: Should only contain 'token_file' and 'relative_path'

        @type  relative_path: str
        @param relative_path: Final path for download

        @return: call __error_torrent() if no answer,
        C_SUCCESS(=0) and Rtorrent answer otherwise
        """
        self.stop_download(hash_file)
        self.set_relative_path_for_dl(hash_file, relative_path)
        self.start_download(hash_file)
        return True

    @aFeature
    def validate(self, hash_pathes):
        """validate the relative_path of  a new torrent

        @type  hash_pathes: dict
        @param request: Should only contain 'token_file' and 'relative_path'

        @return: true or false
        """
        ares = {}
        tres = True
        for plan in hash_pathes:
            hashf, relp = plan['hashfile'], plan['relative_path']
            res = self.validate_dl(hashf, relp)
            ares[hashf] = res
            tres = tres and res
        if not tres:
            return ares
        return ares


# ----------------------

    @aFeature
    def set_relative_path_for_dl(self, hash_file, relative_path):
        """change download directory

        @type  relative_path: str
        @param relative_path: relative path

        @type  hash_file: str
        @param hash_file: Torrent infohash

        @return: True or None (False ??)
        """
        relative_path = self.path_dl + '/' + relative_path
        if not os.path.isdir(relative_path):
            logging.info("creating %s" % (relative_path))
            os.makedirs(relative_path)
        self.rtc.d.set_directory(hash_file, relative_path)
        logging.info("set directory base to %s for %s" % (relative_path, hash_file))
        loaded_from = self.get_loaded_file(hash_file)
        tied = self.get_tied_file(hash_file)
        if not tied.endswith(".torrent"):  # already treated
            to_tied = ".".join(loaded_from.split(".")[:-1]) + ".torrent"
            self.set_tied_file(hash_file, to_tied)
            shutil.move(loaded_from, to_tied)

        return

    @aFeature
    def load(self, path, hash_file):
        """Load a .torrent and wait for it to be loaded

        @type  path: str
        @param path: path to torrent file

        @type  hash_file: str
        @param hash_file: torrent infohash
        """
        res = self.rtc.load_verbose(path)
        sleeped = 1
        while hash_file not in self.download_list() :
            logging.info("searching %s in %s" % (str(hash_file), str(self.download_list())))
            sleep(1)
            sleeped += 1
            if sleeped > 15 :
                return False
        return res == 0

    @aFeature
    def get_loaded_file(self, hash_file):
        """get the file the hash_file was loaded from (a .torrent file)

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: path relative to session
        """
        return self.rtc.d.get_loaded_file(hash_file)

    @aFeature
    def get_tied_file(self, hash_file):
        """get the file the hash_file is tied to (a .torrent file)

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: path relative to session
        """
        return self.rtc.d.get_tied_to_file(hash_file)

    @aFeature
    def set_tied_file(self, hash_file, path):
        """Set the file the hash_file is tied to (a .torrent file)

        @type  hash_file: str
        @param hash_file: hash of the file

        @type  path: str
        @param path: file to tied to

        @return: path relative to session
        """
        return self.rtc.d.set_tied_to_file(hash_file, path)

    @aFeature
    def xmlrpc(self, function, args = None):
        """Direct call to xmlrpc function

        @type  function: str
        @param function: function name

        @type  args: str
        @param args: function arguments

        @return xmlrpc return
        """
        rtc = xs.RTorrentXMLRPCClient(self.host)
        if args :
            args = [ arg.replace('|',',').strip() for arg in args.split(',')]
            return rtc.__getattr__(function)(*args)
        else:
            return rtc.__getattr__(function)()

    @aFeature
    def status_exchange_legacy(self, hash_file = []):
        """Get status of a hash_file

        @type  hash_file: list
        @param hash_file: list of infohashes

        @return: a description of the download
        """
        hash_files = self.get_hash_files(hash_file)
        res = []
        for hash_file in hash_files :
            #self._reread_torrent_trace()
            tmpres = {'hash_file': hash_file,
                      'size': self.get_size(hash_file),
                      'downloaded': self.get_size_done(hash_file),
                      'started': self.is_started(hash_file),
                      'priority': self.get_priority(hash_file),
                      'status': "pending",
                      'up': self.get_up_rate(hash_file),
                      'down': self.get_down_rate(hash_file),
                      'ratio': float(self.get_completed_chunk(hash_file)) / self.get_size_in_chunk(hash_file) * 100,
                      'ETA': self.get_eta(hash_file),
                      'file': self.get_path_file(hash_file),
                      'mesg': self.msg(hash_file),
                      'coherence': self.coherence(hash_file),
                      'loaded_from' : self.get_loaded_file(hash_file),
                      'tied_to' : self.get_tied_file(hash_file),
                      'peers': self.get_peers(hash_file),
            # 'duplicates': json.loads(self.torrent_trace.get("DUPLICATE", hash_file.lower())) if self.torrent_trace.has_option("DUPLICATE", hash_file.lower()) else [],
            # 'copies': json.loads(self.torrent_trace.get("COPY", hash_file.lower())) if self.torrent_trace.has_option("COPY", hash_file.lower()) else [],
            # 'post': json.loads(self.torrent_trace.get("POST", hash_file.lower())) if self.torrent_trace.has_option("POST", hash_file.lower()) else [],
                  }

            if self.is_hash_checking(hash_file):
                tmpres['status'] = "preparating"
            if self.is_hash_checked(hash_file):
                tmpres['status'] = "ready"
            if tmpres['down'] > 0:
                tmpres['status'] = "downloading"
            if tmpres['up'] > 0:
                tmpres['status'] = "uploading"
            if tmpres['down'] > 0 and tmpres['up'] > 0:
                tmpres['status'] = "exchanging"
            tmpres['age'] = os.path.getmtime(tmpres['file'][0])
            res.append(tmpres)
        return res

    @aFeature
    def status_view(self, view = ''):
        fields = ["hash_file", 'size', 'downloaded', 'started', 'priority', 'up', 'down', 'completed_chunk',
                  'chunk', 'msg', 'loaded_from', 'tied_to', 'age', "is_checking", "is_checked", 'file', 'peers']
        values = self.rtc.d.multicall(view, 'd.hash=', 'd.get_size_bytes=', 'd.get_bytes_done=',
                                      'd.is_open=', 'd.get_priority=', 'd.get_up_rate=', 'd.get_down_rate=',
                                      'd.get_completed_chunks=', 'd.get_size_chunks=',
                                      'd.get_message=', 'd.get_loaded_file=', 'd.get_tied_to_file=', 'd.get_creation_date=',
                                      'd.is_hash_checking=', 'd.is_hash_checked=', 'f.multicall=,,f.get_frozen_path=,f.is_created=',
                                      'p.multicall=,,p.get_address=,p.get_down_rate=, p.get_up_rate=')
        # 'duplicates': json.loads(self.torrent_trace.get("DUPLICATE", hash_file.lower())) if self.torrent_trace.has_option("DUPLICATE", hash_file.lower()) else [],
        # 'copies': json.loads(self.torrent_trace.get("COPY", hash_file.lower())) if self.torrent_trace.has_option("COPY", hash_file.lower()) else [],
        # 'post': json.loads(self.torrent_trace.get("POST", hash_file.lower())) if self.torrent_trace.has_option("POST", hash_file.lower()) else [],
        res = []
        for dl in values :
            # don't take last 2 elements, they are list for files or peer
            desc = dict(zip(fields, dl))
            desc['started'] = (desc['started'] == 1)
            desc['status'] = "pending"
            desc['ratio'] = float(desc['completed_chunk'])/float(desc['chunk']) * 100

            # treat coherence
            if desc['started'] == 0: #file not open, no coherence problem possible
                desc['coherence'] = True
                # if open, the file should exist :
            else :
                desc['coherence'] = desc['file'][0][-1] == 1
            
            # get file (in a proper format
            desc['file'] = desc['file'][0][1]

            # treats peers
            peers = desc['peers']
            desc['peers'] = []
            for peer in peers :
                desc['peers'].append(dict(zip(['token', 'ip', 'upload_rate', 'download_rate'], peer)))



            desc['ETA'] = -1
            if int(desc['down']) == 0:
                if desc['size'] == desc['downloaded']:
                    desc['ETA'] = 0
            else:
                desc['ETA'] = (float(desc['size']) - float(desc['downloaded'])) / float(desc['down'])

            if desc['is_checking']:
                desc['status'] = "preparating"
            if desc['is_checked']:
                desc['status'] = "ready"
            if int(desc['down']) > 0:
                desc['status'] = "downloading"
            if int(desc['up']) > 0:
                desc['status'] = "uploading"
            if int(desc['down']) > 0 and int(desc['up']) > 0:
                desc['status'] = "exchanging"

            res.append(desc)
        return res

    @aFeature
    def status_exchange(self, hash_file = []):
        """Get status from infohashes

        @type  hash_file: str, or list
        @param hash_file: hash_file name

        @return: a description of the download
        """
        hash_files = self.get_hash_files(hash_file)
        all_res = self.status_view()
        res = []
        if not hash_files :
            return all_res
        for desc in all_res :
            if desc['hash_file'] in hash_files :
                res.append(desc)
        return res

    @aFeature
    def get_creation_date(self, hash_file) :
        """
        """
        return self.rtc.d.get_creation_date(hash_file)

    @aFeature
    def status_download(self):
        """Get status of hash_files that are downloadding

        @return: a description of the download
        """
        return self.status_view('leeching')

    @aFeature
    def status_upload(self):
        """Get status of hash_files that are uploading

        @return: a description of the download
        """
        return self.status_view('seeding')

    @aFeature
    def status_paused(self):
        """Get status of hash_files that are paused

        @return: a description of the download
        """
        res = []
        return self.status_view('stopped')

    @aFeature
    def list_ended_files(self):
        """Get status of hash_files that are ended

        @return: a description of the download
        """
        return self.status_view('complete')

    @aFeature
    def get_path_file(self, hash_file):
        """Get the real path or the file downloaded

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: path of file
        """
        return self.rtc.f.multicall(hash_file, '', 'f.get_frozen_path=')[0][0],

    @aFeature
    def get_size(self, hash_file):
        """Get the total size in bytes of a specific download

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: Download size in bytes
        """
        return self.rtc.d.get_size_bytes(hash_file)

    @aFeature
    def get_size_done(self, hash_file):
        """Get the total size in bytes of a specific download

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: Download size in bytes
        """
        return self.rtc.d.get_bytes_done(hash_file)


    @aFeature
    def get_peers(self, hash_file):
        """Get list of peers that are used for a torrent

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: a list of peer
        """
        peers = self.rtc.p.multicall(hash_file, "", "p.get_address=",
                                     "p.get_down_rate=", "p.get_up_rate=")
        res = []

        for peer in peers:
            res.append({'ip': peer[0],
                        'upload_rate': peer[1],
                        'download_rate': peer[2],
                        'token_site': ''})
        return res


    @aFeature
    def get_size_in_chunk(self, hash_file):
        """Get the total size of a specific download

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: Download size
        """
        return self.rtc.d.get_size_chunks(hash_file)


    @aFeature
    def get_completed_chunk(self, hash_file):
        """Get number of complete downloaded chunks

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: Number of complete downloaded chunks
        """
        return self.rtc.d.get_completed_chunks(hash_file)


    @aFeature
    def get_ratio(self, hash_file):
        """Get download ratio

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: Ratio download (float)
        """
        return float(self.get_completed_chunk(hash_file)) / \
            self.get_size_in_chunk(hash_file) * 100


    @aFeature
    def get_eta(self, hash_file):
        """Get estimated downloading time left

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: Estimated time left in seconds

        """
        down_rate = self.rtc.d.get_down_rate(hash_file)

        if down_rate == 0:
            if self.rtc.d.get_bytes_done(hash_file) == self.rtc.d.get_size_bytes(hash_file):
                return 0
            return -1
        return (self.rtc.d.get_size_bytes(hash_file) - self.rtc.d.get_bytes_done(hash_file)) / self.rtc.d.get_down_rate(hash_file)


    @aFeature
    def get_up_rate(self, hash_file):
        """Get upload rate for a specific download

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: Upload rate in ???
        """
        return self.rtc.d.get_up_rate(hash_file)


    @aFeature
    def get_down_rate(self, hash_file):
        """Get download rate for a specific download

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: Download rate in ???
        """
        return self.rtc.d.get_down_rate(hash_file)


    @aFeature
    def is_hash_checked(self, hash_file):
        """Verify if a specific download hash has been checked

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: True or False
        """
        return self.rtc.d.is_hash_checked(hash_file) == 1


    @aFeature
    def is_hash_checking(self, hash_file):
        """Verify if a specific download hash is being checked

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: True or False
        """
        return self.rtc.d.is_hash_checking(hash_file) == 1


    @aFeature
    def is_started(self, hash_file):
        """Verify if a specific download hash is being checked

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: True or False
        """
        return self.rtc.d.is_open(hash_file) == 1


    @aFeature
    def msg(self, hash_file):
        """get the messages associated with hash_file

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: str, message
        """
        return self.rtc.d.get_message(hash_file)


    @aFeature
    def coherence(self, hash_file):
        """Verify if a specific download hash is coherent, ie its file are here and well

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: True or False
        """
        # if not open, no notion of coherence
        if self.rtc.d.is_open(hash_file) == 0:
            return True
        # if open, the file should exist :
        return self.rtc.f.multicall(hash_file, '', 'f.is_created=')[0][0] == 1


    @aFeature
    def add_peer(self, hash_file, peer):
        """Add a specific peer to a specific download

        @type  hash_file: str
        @param hash_file: hash of the file

        @type  peer: str
        @param peer: Peer IP

        @return: True or False
        """
        return self.rtc.add_peer(hash_file, peer) == 1



    @aFeature
    def get_priority(self, hash_file):
        """Get download priority (0-3)

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: Priority
        """
        return self.rtc.d.get_priority(hash_file)

    @aFeature
    def set_priority(self, hash_file, value):
        """Set download priority

        @type  hash_file: str
        @param hash_file: hash of the file

        @type  value: int
        @param value: priority (0-3)

        @return: True or False
        """
        res = self.rtc.d.set_priority(hash_file, int(value)) == 0
        self.rtc.d.update_priorities(hash_file)
        return res

    @aFeature
    def get_priority_str(self, hash_file):
        """Get download priority as a string (0=off, 1=low, 2=normal, 3=high)

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: Priority as a string
        """
        return self.rtc.d.get_priority_str(hash_file)


    @aFeature
    def start_download(self, hash_file):
        """Start a dl given its hash_file

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: True if dl started
        """
        return self.rtc.d.start(hash_file)


    @aFeature
    def stop_download(self, hash_file):
        """Stop a dl given its hash_file

        @type  hash_file: str
        @param hash_file: hash of the file

        @return: True if dl started
        """
        return self.rtc.d.stop(hash_file)


    @aFeature
    def start_all(self):
        """Start all known downloads

        @return: True
        """
        self.rtc.d.multicall('', 'd.start=')
        return True

    @aFeature
    def stop_all(self):
        """Stop all known downloads

        @return: True
        """
        self.rtc.d.multicall('', 'd.stop=')
        return True

    @aFeature
    def is_all_started(self):
        """Check if all downloads are started

        @return: True if all downloads are started
        """
        #we test the size of the list of stopped download
        # if it's empty, all is started
        return len(self.download_list('stopped')) == 0

    @aFeature
    def is_all_stopped(self):
        """Check if all downloads are stopped

        @return: True if all downloads are stopped
        """
        #we test the size of the list of started download
        # if it's empty, all is stopped
        return len(self.download_list('started')) == 0



    @aFeature
    def is_present(self, hash_file) :
        """Check if a specific download is present

        @type  hash_file: str
        @param hash_file: infohash to check

        @return: True if download is present
        """
        return (hash_file in self.download_list())



    @aFeature
    def erase(self, hash_file):
        """Erase as hash_file (this will not remove file)

        @type  hash_file: str
        @param hash_file: infohash to erase

        @return True or False
        """
        return self.rtc.d.erase(hash_file)


    @aFeature
    def remove_file(self, hash_file, follow = False):
        """Erase as hash_file (this WILL remove the file)

        @type  hash_file: str
        @param hash_file: infohash to erase

        @return True or False
        """
        files = self.get_path_file(hash_file)
        errors = []
        link = ''
        for f in files:
            try:
                link = ''
                if follow and os.path.islink(f) :
                    link = os.readlink(f)
                os.remove(f)
                if follow and link :
                    os.remove(link)

                if not os.listdir(os.path.dirname(f)) :
                    os.rmdir(os.path.dirname(f))
            except:
                errors.append(f)
        self.rtc.d.erase(hash_file)
        return {'errors' : errors}
    

# -------- 

    @aFeature
    def statfs(self):
        """Prepare a new torrent given a path and tocken

        @type  request: dict
        @param request: Should be empty

        """
        l = {"path_session" : self.path_session, "path_dl" : self.path_dl, "path_log" : self.path_log}
        res = {}
        for n in l:
            s = os.statvfs(l[n])
            res[n] = (s.f_bavail * s.f_frsize)

        limit_size = self.max_dl_size
        if self.max_dl_size < 0 :
            return res

        res['free_dl'] = self.free_dl()
        return res

    @aFeature
    def free_dl(self):
        """Prepare a new torrent given a path and tocken

        @type  request: dict
        @param request: Should be empty

        """
        limit_size =  self.max_dl_size
        if limit_size < 0 :
            return -1
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.path_dl):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        freespace = limit_size - total_size
        return freespace


# ----- logs management


    @aFeature
    def get_log(self, type_log = 'client', nb_line = 10):
        """Get log file

        @type  request: dict
        @param request: can have nb and file params, must have type

        @return: C_SUCCESS(=0)
        and the conntent of the last nb lignes of the curent
        """

        if type_log not in ['rtorrent', 'client']:
            return C_PARAM_ERROR, "log type %s doesn't exist" % type_log
        res = []
        if type_log == 'client':
            res = lastLine(self.bokor.configuration.get_log_file(), int(nb_line))
        if type_log == 'rtorrent':
            res = lastLine(self.path_log + "rtorrent.log", int(nb_line))
        return res

    @aFeature
    def list_logs(self, type_log = None):
        """Request the list of all log files

        @type  request: dict
        @param request: can contain type as 'rtorrent', 'client' or 'prepare']

        @return: return list of logs file
        (with a filter on type if type is present)
        """
        res = []
        if type_log not in [None, 'rtorrent', 'client']:
            type_log = None

        lfile = []
        if type_log :
            if type_log == "client":
                lfile = glob.glob('%s/%s*' %
                                   (os.path.dirname(self.bokor.configuration.get_log_file()),
                                   type_log))
            if type_log == "rtorrent":
                lfile = glob.glob('%s/%s*' %
                                  (self.path_log,
                                  type_log))
        else :
            lfile = [self.path_log + '/' + x
                     for x in os.listdir(self.path_log) ]
            if self.bokor.configuration.get_log_file() :
                lfile += [ self.bokor.configuration.get_log_file() + '/' + x
                           for x in os.listdir(os.path.dirname(self.bokor.configuration.get_log_file()))]
        lfile = sorted(set(lfile))
        for f in lfile:
            if os.path.isfile(f) and os.access(f, os.R_OK):
                res.append({'file': f,
                            'age': os.path.getmtime(f),
                            'size': os.stat(f).st_size})
        return res




# bw test




    @aFeature
    def bwtest(self, slow = False):
        """Test the speed of the bandwidth down, up, ping

        @type request: request should be empty
        @param request: empty

        @return: C_SUCCESS(=0) and a dict with three key "download_speed, upload_speed, ping"
        """

        if self.status_rtorrent():
            self._bokor_code =  BW_ERROR 
            return "rtorrent running"
        exclude = []
        if slow :
            exclude = ['/5M', '/10M']
        ret = {}
        try:
            s_dl = bwt.download(exclude)
            s_up = bwt.upload()
            s_pg = bwt.ping()
        except:
            self._bokor_code =  BW_ERROR 
            return "Something went wrong with bandwith test"
        ret["download_speed"] = s_dl / 1024
        ret["upload_speed"] = s_up / 1024
        ret["ping"] = s_pg
        return ret



# -----------------------------------------------------------------------------

    @aFeature
    def external_configuration(self, token_tmp = None):
        """open a web browser to begin or continue configuration

        """
        if token_tmp != self.bokor.token:
            self.bokor.token = token_tmp

        webbrowser.open_new_tab(self.get("slave", "url_conf") +
                                '?token=%s&init=False' %
                                (self.bokor.token))
        return True

    @aFeature
    def update(self, conf):
        """Update configuration file based on a new one

        @type  request: dict
        @param request: should only contains 'conf', path of the new conf

        @return: C_SUCCESS(=0)
        """
        for section in conf:
            for option in conf[section]:
                if section == "upload" and option == "config":
                    continue
                self.bokor.configuration.set(section, option, conf[section][option])
                logging.info("update : set (%s, %s) to  %s" %
                             (section, option, conf[section][option]))
        self.bokor.configuration.write_conf()
        return self.bokor.reboot(True)

