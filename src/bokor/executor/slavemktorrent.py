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
@brief process orders for bokor mktorrent functionnalities
"""

import os
import subprocess
import imp
import logging

from bokor.interface.unsafesocket import UnsafeSocketClient

from bokor.executor.executor import Executor
from bokor.constants.error import *
from bokor.constants.system import *
from bokor.executor.executor import  aFeature, anExecutor, aPreProcess, aPostProcess
from bokor.configuration.configurable import Configurable
from bokor.memory.mktorrentmemory import MkTorrentMemory

from bokor.executor.plugins.slavemktorrent.error import *
from bokor.executor.plugins.slavemktorrent.prepare import *
from bokor.executor.plugins.slavemktorrent.filetree import FileTree


@anExecutor
class SlaveMKTorrent(Configurable):

    dependances = { "configuration" : [] ,
                    "interface" : [UnsafeSocketClient],
                    "transmission" : [],
                    "feature" : []}
    

    needed_configuration = {"upload":
                            {
                                "mktorrent": {'mandatory' : True, 'type' : 'file' , 'permission' : 'rx', 'exist' : True},
                                "user": {'mandatory' : True, 'type' : 'string'},
                                "server": {'mandatory' : True, 'type' : 'host'},
                                "prepare": {'mandatory' : True, 'type' : 'file' , 'permission' : 'r', 'exist' : True},
                                "password": {'mandatory' : True, 'type' : 'string'},
                                "notify_url": {'mandatory' : True, 'type' : 'string'},
                            },
                            "memory" :
                            {
                                "sqlitedir": {'mandatory' : False, 'type' : 'file' , 'permission' : 'drwx', 'exist' : True}, 
                            },
                        }



    def __init__(self, bokor):
        self.bokor = bokor
        self.cinegoserv = self.get("slave", "master")
        self.path_dl = self.get("rtorrent", "path_dl").rstrip('/') + '/'
        self.path_session = self.get("rtorrent", "path_session").rstrip('/') + '/'
        self.path_log = self.get("rtorrent", "path_log").rstrip('/') + '/'
        self.tmp = '/tmp' #FIXME, in threading structure
        self.mktorrent = self.get("upload", "mktorrent")
        self.ftp_server = self.get("upload", "server")
        self.ftp_user = self.get("upload", "user")
        self.ftp_password = self.get("upload", "password")
        self.notify = self.get("upload", "notify_url")
        self.db = self.get('memory', 'sqlitedir', '/tmp')  + '/' + 'mktorrent.db'
        self.memory = MkTorrentMemory(self.db)

        
        self.prepare_thread = PrepareTorrentThread(self.db, self.mktorrent, self.bokor.token, self.tmp,
                                                   self.path_session, self.path_dl, self.notify,
                                                   self.ftp_server, self.ftp_user, self.ftp_password)


        self.prepare_thread.setName('prepare')
        self.prepare_thread.start()

    @aFeature
    def get_assets(self, field = None, value = None):
        return self.memory.get_assets(field, value)

    @aFeature
    def add_file(self, iddl, token_file, path_file, tracker_url):
        res = None
        if os.path.isdir(path_file) :
            idassets = self.prepareTREE(iddl, tracker_url, token_file, path_file)
        else:
            idassets = [self.prepare_file(iddl, tracker_url, token_file, path_file, None, 1)]
        # os.remove('/tmp/' + token_site + '_' + token)
        if not idassets :
            self._bokor_code = PREPARE_ERROR
        
        return idassets


    def prepare_file(self, iddl, tracker_url, token_file, path_file,
                      relative_path=None, nb_assets=0):
        """Prepare the upload of a single file

        @type  tracker_url: str
        @param tracker_url: url for opentracker

        @type  token_file: str
        @param token_file: token of the file

        @type  path_file: str
        @param path_file: path of the TREE

        @type  asset: str
        @param asset: hash of the TREE file torrent, "none" for a real single file

        @type  relative_path: str
        @param relative_path: final path to put the downloaded file

        @type  assets: str
        @param assets: number of assets linked to this file ('0' by default)

        @return: returns the token of the uploaded file
        """

        apath = os.path.expanduser(path_file)
        asset = self.memory.get_assets('file', apath)
        new_asset = { 'id' : None,
                      'iddl' : iddl,
                      'info_hash' : None,
                      'relative_path' : relative_path.strip('/') if relative_path else None,
                      'file' : apath, 
                      'link' : None, 
                      'tmp_torrent' : None, 
                      'torrent_file' : None, 
                      'ftp_url' : None,
                      'size_torrent' : None,
                      'tracker' : tracker_url,
                      'begin' : int(time.time()), 
                      'status' : 'new', 
                      'file_exist' : os.path.exists(apath), 
                      'file_access' : os.path.isfile(apath), 
                      'mktorrent_start' : None, 
                      'send_start' : None, 
                      'end' : None, 
                      'error' : None }
        if not new_asset['file_exist'] :
            #new_asset['status'] = 'error'
            new_asset['error'] = "file %s doesn't exist"%apath
        elif not new_asset['file_access'] :
            #new_asset['status'] = 'error'
            new_asset['error'] = "can't read file %s"%apath

        if asset :
            asset = asset[0]
            #new_asset['status'] = 'known'
            new_asset['info_hash'] = asset['info_hash']
            new_asset['torrent_file'] = asset['torrent_file']
            new_asset['ftp_url'] = asset['ftp_url']
            new_asset['size_torrent'] = asset['size_torrent']
            new_asset['error'] = "file already treated, see %s"%asset['id']

        if new_asset['status'] != 'new' :
            new_asset['end'] =  int(time.time())

        new_asset['id'] = self.memory.create_asset(new_asset)
        print new_asset['id'], new_asset['error']
        return new_asset['id']
        

        

    def prepareTREE(self, iddl, tracker_url, token_file, path):
        """Prepare a TREE file: create one torrent for TREE_xxx.xml itself and one for each asset

        @type  tracker_url: str
        @param tracker_url: url for opentracker

        @type  token_file: str
        @param token_file: token of the file

        @type  path: str
        @param path: path of the TREE

        @return: returns the token of the uploaded file
        """
        logging.info("prepare TREE %s %s %s %s %s" % (iddl, tracker_url,
                                                     self.bokor.token, token_file, path))
        tree = FileTree(path)
        afiles = tree.assets

        ref_path = os.path.dirname(path)

        assets = []
        for relative_path, afile in afiles:

            path_to_file = ref_path + "/" + "/".join(relative_path.split("/")[1:]) + "/" + afile
            assets.append(self.prepare_file(iddl, tracker_url, token_file,
                                         path_to_file, relative_path,
                                          len(afiles)))

        return assets


    @aFeature
    def status_prepare_thread(self) :
        return self.prepare_thread.isAlive()



    @aFeature
    def start_prepare_thread(self) :
        if not self.prepare_thread.isAlive() :
            self.prepare_thread.start()


    @aFeature
    def delete_assets(self, filters, value, compare = "="):
        return self.memory.delete_assets(filters, value, compare)


    @aFeature
    def delete_asset(self, idasset):
        return self.delete_assets('id', idasset)
    
