#!/usr/bin/env python
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

@file constants/system.py
@author Olivier ANDRE <zitune@bearstech.com>
@author Maurice AUDIN <maudin@bearstech.com>
@date 2014
@brief fs explorer functions
"""

from bokor.executor.executor import  aFeature, anExecutor, aPreProcess, aPostProcess
from bokor.configuration.configurable import Configurable
from bokor.constants.error import *
import grp
import pwd
import sys
import platform
import os
import stat
import locale
import time
from shutil import copyfile

@anExecutor
class Explorer(Configurable):

    
    def __init__(self, bokor) :
        self.bokor = bokor
        
    #Do locale sensitive sort of files to list
    #locale.setlocale(locale.LC_ALL,'')


    #setup global variables (dictionary)
    now = int(time.time())
    recent = now - (6*30*24*60*60) #6 months ago



    #function to get info from mode
    @aFeature
    def get_mode_info(self, mode, filename, uid, gid):

        perms="-"
        link=""
        user_right = {'read': False, 'write' : False, 'exe' : False,
                  'is_dir' : False, 'is_link' : False, 'link' : None}



        whoami = os.getuid()
        group = os.getgid()
    
        if stat.S_ISDIR(mode):
            perms="d"
            user_right['is_dir'] = True 
        elif stat.S_ISLNK(mode):
            perms="l"
            user_right['is_link'] = True         
            user_right['link'] = os.readlink(filename)
        mode=stat.S_IMODE(mode)
        for who in "USR", "GRP", "OTH":
            for what in "R", "W", "X":
                #lookup attributes at runtime using getattr
                if mode & getattr(stat,"S_I"+what+who):
                    perms=perms+what.lower()
                    if (who == 'USR' and uid == whoami ) \
                           or (who == 'GRP' and gid == group ) :
                        if what == 'R' : user_right['read'] = True 
                        if what == 'W' : user_right['write'] = True 
                        if what == 'X' : user_right['exe'] = True 
                else:
                    perms=perms+"-"
        #return multiple bits of info in a tuple
        return (perms, user_right)

    @aFeature
    def ls_files(self, files) :
    
        perms = ""
        res = []
        #Now process each file in list using a for loop
        for filename in files:
            desc = {'basename' : os.path.basename(filename),
                    'path' : os.path.abspath(filename),
                    'name' : filename,
                    'exist' : False,
                    'read' : False,
                    'write' : False,
                    'read': False,
                    'write' : False,
                    'exe' : False,
                    'is_dir' : False,
                    'is_link' : False,
                    'link' : None,
                    'user' : None,
                    'group' : None,
                    'perm' : None,
                    'size' : 0,
                    'time' : 0,
                    }
            try: #exceptions
                #Get all the file info
                stat_info=os.lstat(filename)
                desc['exist'] = True
            except :
                sys.stderr.write("%s: No such file or directory\n" % filename)
                continue
        
            desc['perm'], user_right = self.get_mode_info(stat_info.st_mode, filename, stat_info.st_uid, stat_info.st_gid)
            desc.update(user_right)
        
        
            try:
                desc['user'] = pwd.getpwuid(stat_info.st_uid)[0]
            except KeyError:
                desc['user'] = stat_info.st_uid

            try:
                desc['group'] = grp.getgrgid(stat_info.st_gid)[0]
            except KeyError:
                desc['group'] = stat_info.st_gid

            desc['size'] = stat_info.st_size
            
            #Get time stamp of file
            desc['time'] = stat_info.st_mtime
            res.append(desc)
        return res


    @aFeature
    def ls(self, path) :
        files = []
        try :
            if os.path.isdir(path) :
                files=[path + '/' + filename for filename in os.listdir(path)]
                files.sort(locale.strcoll)
        except Exception as error:
            self._bokor_code = UNEXCEPTED_EXCEPTION;
            msg = str(sys.exc_info())
            return msg
        files = [path] + files
        return self.ls_files(files)



    @aFeature
    def remove(self, path) :
        return os.remove(path)



    @aFeature
    def cp(self, path_origin, path_dest) :
        copyfile(path_origin, path_dest)
        return True


    @aFeature
    def mkdir(self, path) :
        os.mkdir(path)
        return True


    @aFeature
    def os_flavor(self) :
        try:
            linux = platform.linux_distribution()
        except:
            linux = "N/A"  
        desc = {"python": sys.version.split('\n'), 
                "dist" : str(platform.dist()),
                "linux_distribution" : linux,
                "system" : platform.system(),
                "machine" : platform.machine(),
                "platform" : platform.platform(),
                "uname" : platform.uname(),
                "version" : platform.version(), 
                "mac_ver" : platform.mac_ver(),
            }
        return desc

if __name__ == '__main__' :
    #simple command line processing to get files (if, list)
    if len(sys.argv) == 1:
        fpath="."
    else:
        fpath=sys.argv[1]
    import pprint, sys
    
    pp = pprint.PrettyPrinter(indent=1)
    pp.pprint(lstree(fpath))


