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
@brief post thread for post dl operations
"""
import os
import sys
import errno
import logging
import shutil
import subprocess
import urllib
import re
from ftplib import FTP
from time import sleep, time
from tempfile import mkstemp
import logging


from bokor.memory.postdlmemory import PostMemory

from threading import Thread
from random import randint
import time

class PostThread(Thread):


    def __init__(self, db):
        Thread.__init__(self)
        logging.info("init post thread")

        self.setDaemon(True)
        self.memory = PostMemory(db)


    def run(self):
        while True :
            time.sleep(5)

            # get all rp to treat (status todo)
            to_treat = self.memory.get_relative_path('status', 'todo')
            for rp in to_treat :
                rp['status'] = 'treating'
                self.memory.update_relative_path(rp)

                # for all movement in rp
                for movement in rp['movements'] :
                    try :
                        self.treat_movement(rp, movement)
                    except Exception as e:
                        self.movement_error(movement, "unknown : %s"%( str(e)))
                        rp['status'] = 'error'
                if rp['status'] == 'treating' :
                    rp['status'] = 'done'
                self.memory.update_relative_path(rp)






    def treat_movement(self, rp, movement):
        if movement['status'] in ['error', 'done']:
            return

        now = int(time.time())
        movement['begin'] = now
        movement['status'] = 'treating'
        self.memory.update_movement(movement)

        # checking sources
        movement['src_exist'] = True
        if not os.path.exists(rp['src']) :
            now = int(time.time())
            movement['src_exist'] = False
            movement['status'] = 'error'
            movement['end'] = now
            movement['error'] = "source file : %s does not exist"%(rp['src'])
            self.memory.update_movement(movement)
            return

        # adapt in function of protocol
        if movement['protocol'] == 'cp' :
            self.do_cp(movement, rp)
            return
        if movement['protocol'] == 'ftp' :
            self.do_ftp(movement, rp)
            return
        now = int(time.time())
        movement['status'] = 'error'
        movement['end'] = now
        movement['error'] = "protocol %s not known"%(movement['protocol'])
        self.memory.update_movement(movement)
        rp['status'] = 'done'
        self.memory.update_relative_path(rp)




    def do_cp(self, movement, rp):
        #init of exist
        movement['dst_exist'] = True
        if not os.path.isdir(os.path.dirname(movement['dst_url'])) :
            movement['status'] = 'creating'
            movement['dst_exist'] = False
            self.memory.update_movement(movement)
            try :
                os.makedirs(os.path.dirname(movement['dst_url']))
            except Exception as e:
                movement['dst_access'] = False
                self.movement_error(movement, "error creating dirs %s"%(str(e)))
                return
        movement['status'] = 'ready'
        self.memory.update_movement(movement)
        try :
            movement['status'] = 'copying'
            self.memory.update_movement(movement)
            shutil.copy(rp['src'], movement['dst_url'])
        except Exception as e:
            movement['dst_access'] = False
            self.movement_error(movement, "error during copy %s"%( str(e)))
            return
        now = int(time.time())
        movement['status'] = 'done'
        movement['end'] = now
        self.memory.update_movement(movement)




    def do_ftp(self, movement, rp):
        args = re.match('ftp://(?P<login>[^:]*):(?P<pwd>[^@]*)@(?P<host>[^/]*)(?P<path>.*)', movement['dst_url'])
        if not args :
            self.movement_error(movement, "dst_url : %s  is not a valid ftp url")
            return
        login = args.group('login')
        pwd = args.group('pwd')
        host = args.group('host')
        path = args.group('path')
        movement['status'] = 'connecting'
        self.memory.update_movement(movement)

        # try to connect

        try :
            ftp = FTP(host, login, pwd, timeout=60)
        except Exception as e:
            movement['dst_access'] = False
            self.movement_error(movement, "error while connecting ftp : %s"%(str(e)))
            return

        movement['status'] = 'connected'
        self.memory.update_movement(movement)

        # try to go to directory

        try :
            self.ftp_chdir(os.path.dirname(path), ftp, movement)
        except Exception as e:
            movement['dst_access'] = False
            self.movement_error(movement, "error while browsing ftp : %s"%(str(e)))
            return
        # try to send

        try :
            with open(rp['src'], 'rb') as f :
                movement['status'] = 'sending'
                self.memory.update_movement(movement)
                ftp.storbinary('STOR ' + os.path.basename(rp['src']) , f)
                logging.debug("push FTP done")
        except Exception as e:
            self.movement_error(movement, "error while sending to ftp : %s"%(str(e)))
            return

        now = int(time.time())
        movement['status'] = 'done'
        movement['end'] = now
        self.memory.update_movement(movement)

    def movement_error(self, movement, error):
        logging.error(error)
        now = int(time.time())
        movement['status'] = 'error'
        movement['error'] = error
        movement['end'] = now
        self.memory.update_movement(movement)




    def ftp_chdir(self, dir, ftp, movement):
        """Change ftp directory, create if necessary

        @type  dir: str
        @param dir: path of the directory

        @type  ftp: ftplib.FTP object
        @param ftp: FTP object already initialized

        @return: none
        """
        logging.info("ask to push in %s"%dir)
        dirs = dir.split("/")

        for f in dirs :
            if not f : continue
            logging.info("looking for sub path %s"%f)

            if not self.ftp_directory_exists(f, ftp) :
                logging.info("creating sub path %s"%f)
                movement['status'] = 'creating'
                movement['exist'] = False
                self.memory.update_movement(movement)
                ftp.mkd(f)
            logging.info("moving to sub path %s"%f)
            ftp.cwd(f)
        movement['status'] = 'ready'
        self.memory.update_movement(movement)


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
            if f.split()[-1].strip('/') == str(dir).strip('/') and f.upper().startswith('D'):
                return True
        return False
