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

@file memory/mastertorrentmemory.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief function to preprare a .torrent file
"""
import argparse
import os
import sys
import errno
import logging
import shutil
import subprocess
import urllib
from ftplib import FTP
from time import sleep, time
from tempfile import mkstemp



from hashtorrent import  getHash, getSize
from bokor.memory.mktorrentmemory import MkTorrentMemory

from threading import Thread
from random import randint
import time





def force_symlink(file1, file2):
    try:
        os.symlink(file1, file2)
    except OSError, e:
        if e.errno == errno.EEXIST:
            os.remove(file2)
            os.symlink(file1, file2)


class PrepareTorrentThread(Thread):


    def __init__(self, db, mktorrent, token, tmp,
                 path_session, path_dl, notify,
                 ftp_server, ftp_user, ftp_password):
        Thread.__init__(self)
        self.setDaemon(True)
        self.memory = MkTorrentMemory(db)
        self.mktorrent = mktorrent
        self.token = token
        self.tmp = tmp
        self.path_session = path_session
        self.path_dl = path_dl
        self.notify = notify
        self.ftp_server = ftp_server
        self.ftp_user = ftp_user
        self.ftp_password = ftp_password
        
    def run(self):
        while True : 
            time.sleep(5)

            try : 
                to_treat = self.memory.get_assets('status', 'new')
                for asset in to_treat :
                    if asset['error'] :
                        if asset['info_hash'] :
                            asset['status'] = 'known'
                        else :
                            asset['status'] = 'error'
                                                        
                    elif not self.run_mktorrent(asset) or \
                       not self.link_file(asset) or \
                       not self.mv_torrent(asset) or \
                       not self.send_torrent(asset) :
                        if asset['status'] != "known" :
                            asset['status'] = 'error'
                    else :
                        
                        asset['status'] = 'done' if not asset['relative_path'] else "unvalidated"
                    opts = dict(
                        seeder = self.token,
                        infohash = asset['info_hash'],
                        iddl = asset['iddl'],
                        relative_path =  asset['relative_path'],
                        file_name = os.path.basename(asset['file']),
                        status = asset['status'],
                        size = asset['size_torrent'])
                    self.notify_master(asset, opts)
                    now =  int(time.time())
                    asset['end'] = now                
                    self.memory.update_asset(asset)
            except Exception as err:
                logging.error("exception %s"%(err))


    
    def run_mktorrent(self, asset):
        now =  int(time.time())
        tmp_p_torrent = self.tmp + "/" + os.path.basename(asset['file']) + "_" + str(now) + ".torrent_t" 
        asset['tmp_torrent'] = tmp_p_torrent
        asset['mktorrent_start'] = now
        asset['status'] = 'hashing'
        self.memory.update_asset(asset)
        command = '%(mktorrent)s -a "http://%(tracker_address)s/announce?token=%(token)s/" -o "%(ptorrent)s" "%(tfile)s"'\
                  % {'mktorrent': self.mktorrent,
                     'tracker_address': asset['tracker'],
                     'ptorrent': asset['tmp_torrent'],
                     'token': self.token,
                     'tfile': asset['file'],
                  }
        p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        if err :
            asset['error'] = "mktorrent :" + err
            asset['status'] = 'error'
            self.memory.update_asset(asset)
            return False
        asset['info_hash'] = getHash(asset['tmp_torrent'])
        asset['size_torrent'] = os.path.getsize(asset['file'])
        asset['status'] = 'hashed'
        self.memory.update_asset(asset)
        return True




    def link_file(self, asset):
        if asset['relative_path']:
            asset['link'] = self.path_dl + '/' + asset['relative_path'] + '/' + os.path.basename(asset['file'])
        else:
            asset['link'] = self.path_dl + '/' + os.path.basename(asset['file'])
        
        if not os.path.isdir(os.path.dirname(asset['link'])):
            os.makedirs(os.path.dirname(asset['link'])) 
        if os.path.exists(asset['link']) :
            asset['error'] = "Warn : link already exists : " + asset['link']
        force_symlink(asset['file'], asset['link'])
        asset['status'] = 'linked'
        self.memory.update_asset(asset)
        return True

    def mv_torrent(self, asset):
        if asset['relative_path']:
            asset['torrent_file'] = self.path_session + '/' + asset['info_hash'] + '.torrent_upload'
        else:
            asset['torrent_file'] = self.path_session + '/' + asset['info_hash'] + '.torrent_upload_direct'
        if os.path.exists( asset['torrent_file']) :
            asset['status'] = 'known'
            asset['error'] = "torrent_file already exists : " + asset['torrent_file']
            self.memory.update_asset(asset)
            return False
        shutil.copy(asset['tmp_torrent'], asset['torrent_file'])  
        asset['status'] = 'local'
        self.memory.update_asset(asset)
        return True

    def send_torrent(self, asset) :
        now =  int(time.time())
        asset['send_start'] = now
        asset['ftp_url'] = 'ftp://' + self.ftp_user + ':' + self.ftp_password + '@' + self.ftp_server + '/' + asset['info_hash'] + ".torrent"
        asset['status'] = 'sending'
        self.memory.update_asset(asset)
        try :
            ftp = FTP(self.ftp_server, self.ftp_user, self.ftp_password)
            msg = ftp.storbinary('STOR ' + asset['info_hash'] + ".torrent", open(asset['tmp_torrent'], 'rb'))
        except Exception as e:
            msg = str(e)
        if not msg.startswith('226-') :
            asset['error'] = "ftp :" + msg
            return False
        asset['status'] = 'send'
        self.memory.update_asset(asset)
        return True


    def notify_master(self, asset, opts) :
        p = subprocess.Popen('curl -L -k -s -o /dev/null "%s?%s"' % (self.notify, urllib.urlencode(opts)),
                             stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        if err :
            asset['error'] = "notify :" + err
            asset['status'] = 'error'
            self.memory.update_asset(asset)

        

