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

@file master/core.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief configuration checker
"""

import os
import ConfigParser
import socket


class ConfigChecker():

    def __init__(self):
        self.type_checker = dict([(method, getattr(self, method)) for method in dir(self) if callable(getattr(self, method))and method.startswith("_check_")])


    def _add_misfit(self, misfit, section, option, msg):
        if section not in misfit:
            misfit[section] = {}
        misfit[section][option] = msg



    def _check_mandatory(self, section, option, field, conf):
        mandatory = False
        if 'mandatory' in field:
            mandatory = field['mandatory']
        if mandatory and not conf.has_section(section):
            conf.add_section(section)
        if mandatory and not conf.has_option(section, option):
            return False
        if mandatory and not conf.get(section, option) :
            return False
        return True


    def _check_string(self, section, option, file, conf):
        s = None
        if conf.has_section(section) and conf.has_option(section, option):
            s = conf.get(section, option)
        if not s:
            return True, "not mandatory, not known"
        return True, "ras"

    def _check_host(self, section, option, file, conf):
        # file is a dict : {'mandatory' : True, 'type' : 'host'}
        # empty permission
        ip = None
        host = None
        if conf.has_section(section) and conf.has_option(section, option):
            host = conf.get(section, option)
        if not host:
            return True, "not mandatory, not known"
        try:
            ip = socket.gethostbyname(host)
        except:
            pass
        if not ip:
            return False, "unable to resolv"
        return True, "ras"

    def _check_int(self, section, option, file, conf):
        # file is a dict : {'mandatory' : True, 'type' : 'int'}
        # empty permission
        i = 42
        s = None
        if conf.has_section(section) and conf.has_option(section, option):
            s = conf.get(section, option)
            try:
                i = int(s)
            except:
                pass
        if not s:
            return True, "not mandatory, not known"
        if not (str(i) == s):
            return False, 'not an int'
        return True, "ras"
            
    def _check_file(self, section, option, file, conf):
        # file is a dict : {'mandatory' : True, 'type' : 'file' , 'exist' : False, 'permission' : 'rx' }
        # empty permission
        perm = file['permission']
        path = None
        msg = ""
        if conf.has_section(section) and conf.has_option(section, option):
            path = conf.get(section, option)
        if not path:   #value not set, is not mandatory if this fucntion is called
            return True, "not mandatory, not known"
        if 'exist' not in file or file['exist']:
            if not os.access(path, os.F_OK):
                return False, "doesn't exist"
        if not os.access(path, os.F_OK):  # file doesn't exist so we look if the right are good for the directory
            
            path = os.path.dirname(path)
            # the directory must have write permission
            perm = perm + 'dw'
            msg = "file doesn't exist, parent directory :"
        if 'd' in perm:
            if not os.path.isdir(path):
                return False, msg + "is not a directory"
        if 'r' in perm:
            if not os.access(path, os.R_OK):
                return False, msg + "doesn't have read permission"
        if 'w' in perm:
            if not os.access(path, os.W_OK):
                return False, msg + "doesn't have write permission"
        if 'x' in perm:
            if not os.access(path, os.X_OK):
                return False, msg + "doesn't have execute permission"
        return True, "ras"



    def check_conf(self, description, conf ):
        misfit = {}
        for section in description:
            for option in description[section]:
                if not self._check_mandatory(section, option, description[section][option], conf):
                    self._add_misfit(misfit, section, option, "is mandatory")
                    continue
                check, msg = True, "Bokor slave don't know how to veryfie that kind of configuration type, %s" % \
                             description[section][option]['type']
                if "_check_" + description[section][option]['type'] in self.type_checker:
                    check, msg = self.type_checker["_check_" + description[section][option]['type']](section, option, description[section][option], conf)
                if not check:
                    self._add_misfit(misfit, section, option, msg)
        return misfit





if __name__ == '__main__':
    import os, pprint
    desc = {
        "rtorrent": {
            "bin": {'mandatory': True, 'type': 'file', 'permission': 'rx', 'exist': True},
            "max_seed": {'mandatory': True, 'type': 'int'},
            "path_tmp": {'mandatory': True, 'type': 'file', 'permission': 'drwx', 'exist': True},
            "port_max": {'mandatory': True, 'type': 'int'},
            "port_min": {'mandatory': True, 'type': 'int'},
            "path_home": {'mandatory': True, 'type': 'file', 'permission': 'drwx', 'exist': True},
            "ci_up": {'mandatory': True, 'type': 'int'},
            "down_kbps": {'mandatory': True, 'type': 'int'},
            "path_done": {'mandatory': True, 'type': 'file', 'permission': 'drwx', 'exist': True},
            "path_log": {'mandatory': True, 'type': 'file', 'permission': 'drwx', 'exist': True},
            "up_kbps": {'mandatory': True, 'type': 'int'},
            "ci_down": {'mandatory': True, 'type': 'int'},
            "path": {'mandatory': True, 'type': 'file', 'permission': 'drwx', 'exist': True},
            "config": {'mandatory': True, 'type': 'file', 'permission': 'rw', 'exist': True},
            "max_leech": {'mandatory': True, 'type': 'int'},
            "ftp_script": {'mandatory': True, 'type': 'file', 'permission': 'r', 'exist': True},
            "path_dl": {'mandatory': True, 'type': 'file', 'permission': 'drwx', 'exist': True},
        },
        "client": {
            "tmp": {'mandatory': True, 'type': 'file', 'permission': 'drwx', 'exist': True},
            "category": {'mandatory': True, 'type': 'string'},
            "socket_keep_alive": {'mandatory': True, 'type': 'int'},
            "socket_idle": {'mandatory': True, 'type': 'int'},
            "ip": {'mandatory': True, 'type': 'host'},
            "server": {'mandatory': True, 'type': 'host'},
            "token": {'mandatory': True, 'type': 'string'},
            "torrent_trace": {'mandatory': True, 'type': 'file', 'permission': 'rw', 'exist': False},
            "socket_max_fail": {'mandatory': True, 'type': 'int'},
            "port": {'mandatory': True, 'type': 'int'},
            },
        "upload": {
            "ftp_user": {'mandatory': True, 'type': 'string'},
            "ftp_server": {'mandatory': True, 'type': 'host'},
            "prepare": {'mandatory': True, 'type': 'file', 'permission': 'r', 'exist': True},
            "mktorrent": {'mandatory': True, 'type': 'file', 'permission': 'rx', 'exist': True},
            "ftp_password": {'mandatory': True, 'type': 'string'},
            "path_upload": {'mandatory': True, 'type': 'file', 'permission': 'rx', 'exist': True},
            },
        "TMS": {
            "libpass": {'mandatory': False, 'type': 'string'},
            "libip": {'mandatory': False, 'type': 'host'},
            "tmsbuffer": {'mandatory': False, 'type': 'file', 'permission': 'drw', 'exist': True},
            "libfolder": {'mandatory': False, 'type': 'string'},
            "liblogin": {'mandatory': False, 'type': 'string'},

            }
    }

    config_file = os.path.realpath(os.path.expanduser("~/.config/cinegop2p.rc"))
    config = ConfigParser.ConfigParser()
    config_fp = open(config_file, 'r')
    config.readfp(config_fp)
    config_fp.close()
    c = ConfigChecker()
    misfit =  c.check_conf(desc, config)
    pp = pprint.PrettyPrinter(indent=1)
    pp.pprint(misfit)


