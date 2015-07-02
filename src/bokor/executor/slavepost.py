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
@brief process post processing of downloaded file
"""

import os
import time
import imp
import logging


from bokor.interface.unsafesocket import UnsafeSocketClient

from bokor.executor.executor import Executor
from bokor.constants.error import *
from bokor.constants.system import *
from bokor.executor.executor import  aFeature, anExecutor, aPreProcess, aPostProcess
from bokor.configuration.configurable import Configurable
from bokor.memory.postdlmemory import PostMemory

from bokor.executor.plugins.slavepost.post import *


@anExecutor
class SlavePost(Configurable):

    needed_configuration = { "rtorrent" :
                             {
                                 "path_session": {'mandatory' : True, 'type' : 'file' , 'permission' : 'drwx', 'exist' : True},
                                 "path_dl": {'mandatory' : True, 'type' : 'file' , 'permission' : 'drwx', 'exist' : True},
                                 "path_log": {'mandatory' : True, 'type' : 'file' , 'permission' : 'drwx', 'exist' : True},
                                 },
                             "post" :
                             {
                                 "protocol" :  {'mandatory' : True, 'type' : 'string'},
                                 "base_url" :  {'mandatory' : False, 'type' : 'string'},
                             },
                             "memory" :
                             {
                                 "sqlitedir": {'mandatory' : False, 'type' : 'file' , 'permission' : 'drwx', 'exist' : True}, 
                             },
                         }

    def __init__(self, bokor):
        self.bokor = bokor
        self.db = self.get('memory', 'sqlitedir', '/tmp')  + '/' + 'post.db'
        self.memory = PostMemory(self.db)
        self.path_session = self.get("rtorrent", "path_session").rstrip('/') + '/' 
        self.path_dl = self.get("rtorrent", "path_dl").rstrip('/') + '/'
        self.path_log = self.get("rtorrent", "path_log").rstrip('/') + '/'
        self.base_url = self.get("post", "base_url", "")
        self.protocol = self.get("post", "protocol")
        self.post_thread = PostThread(self.db)



        self.post_thread.setName('post')
        self.post_thread.start()



    @aFeature
    def get_dst_url(self, src, relative_path) :
        """ compute destination url from a src and a relative path
        """
        dst = ""
        if self.protocol == "ftp" :
            dst = self.base_url
        else :
            if self.base_url :
                dst = self.base_url
            else :
                dst = self.path_dl
        
        dst += '/' + relative_path.rstrip('/') + '/' + os.path.basename(src)
        return dst

    @aFeature
    def create_relative_path(self, infohash, relative_path, src, status) :
        """
        add a new relative path for an asset and add the mouvement
        """
        rp = {'info_hash' : infohash,
              'relative_path' : relative_path,
              'src' : os.path.expanduser(src),
              'status' : status}
        rp['id'] = self.memory.create_relative_path(rp)
        dst = self.get_dst_url(src, relative_path)
        if dst == src :
            return rp
        self.add_mv(rp, dst, status)
        return rp


    @aFeature
    def create_relative_path_if_needed(self, info_hash, relative_path, src, status) :
        rp = self.memory.get_a_relative_path(info_hash, relative_path)
        if not rp :
            rp = self.create_relative_path(info_hash, relative_path, src, status)
            #create a rp and a movement
            return rp
        for movement in rp['movements'] :
            if movement['status'] in ['downloading', 'todo'] :
                return rp
        dst_url = self.get_dst_url(src, relative_path)
        self.add_mv(rp, dst_url, status)
        return rp
        


    

    
    @aFeature
    def add_movement(self, idrp, protocol, dst_url): 
        rp = self.get_rp('id', idrp)
        if not rp :
            self._bokor_code = 701
            return "no idrp valid"
        rp = rp[0]
        rp['status'] = 'todo'
        self.memory.update_relative_path(rp)
        return self.add_mv(rp, dst_url, 'todo')
        
    def add_mv(self, rp, dst_url, status) :
        movement = {"id" : None,
                    "idrp" : rp['id'],
                    "protocol" : self.protocol,
                    "begin" : None,
                    "status" : status,
                    "src_exist" : None, 
                    "dst_url" : dst_url,
                    "dst_exist" : None,
                    "dst_access" : None,
                    "dst_creation" : None,
                    "send_start": None,
                    "end" : None,
                    "error" : None,
                }
        return self.memory.create_movement(movement)
    
    @aFeature
    def get_relative_path(self, hash_file):
        return self.memory.get_relative_path('info_hash', hash_file)


    @aFeature
    def treat_rp(self, idrp):
        rp = self.get_rp('id', idrp)
        if not rp :
            self._bokor_code = 701
            return "no idrp valid"
        rp[0]['status'] = 'todo'
        self.memory.update_relative_path(rp[0])
        return idrp

    @aFeature
    def get_rp(self, filters = None, value = None, compare = "="):
        return self.memory.get_relative_path(filters, value, compare)

    @aFeature
    def get_mv(self, filters = None, value = None, compare = "="):
        return self.memory.get_movements(filters, value, compare)

    
    @aFeature
    def delete_rp(self, filters = None, value = None, compare = "="):
        return self.memory.delete_relative_path(filters, value, compare)


    @aFeature
    def delete_relative_path(self, idrp):
        return self.delete_rp('id', idrp)

    @aFeature
    def delete_mouvement(self, idmv):
        return self.delete_mv('id', idmv)
    
    @aFeature
    def delete_mv(self, filters, value, compare = "="):
        return self.memory.delete_movement(filters, value, compare)

    
    def ftp_directory_exists(self, dir, ftp):
        """ Check if a directory exists in ftp
        
        @type  dir: str
        @param dir: path of directory
        
        @type  ftp: ftplib.FTP object
        @param ftp: FTP object already initialized
        
        @return: True if directory exists, False otherwise
        """
        filelist = []
        ftp.retrlines('LIST',filelist.append)
        
        for f in filelist:
            if f.split()[-1].strip('/') == dir.strip('/') and f.upper().startswith('D'):
                return True
        return False

    @aFeature
    def ls_ftp(self, host=None, login=None, pwd=None, path=None):
        if not host :
            args = re.match('ftp://(?P<login>[^:]*):(?P<pwd>[^@]*)@(?P<host>[^/]*)(?P<path>.*)', self.base_url)
            if not args :
                return "no default values in conf : %s"%self.base_url
            login = args.group('login')
            pwd = args.group('pwd')
            host = args.group('host')
            if (path == None) : path = args.group('path') 

        ftp = FTP(host, login, pwd, timeout=60)

        files = []
        ftp.cwd(path)
        ftp.retrlines('LIST', files.append)
        return files


    @aFeature
    def delete_ftp(self, host, login, pwd, path):
        ftp = FTP(host, login, pwd, timeout=60)
        return ftp.delete(path)



    @aFeature
    def status_post_thread(self) :
        return self.post_thread.isAlive()



    @aFeature
    def start_post_thread(self) :
        if not self.post_thread.isAlive() :
            self.post_thread.start()

    
