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

@file master/handler.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief handle peer connection with a socket
"""


import platform

import logging
import json

from bokor.configuration.configurable import Configurable
from bokor.constants.default import *
from bokor.constants.system import *
from bokor.interface.baseinterface import BaseInterface
from bokor.bocore.action import Action


#use system socket in cygwin case
#if not OS.startswith('CYGWIN') :
#    import gevent.socket as socket
#else:
#    import socket
import socket


class UnsafeSocketClient(BaseInterface) :
    configuration = {"slave" :
                     {
                         "socket_keep_alive": {'mandatory': True, 'type': 'int'},
                         "socket_idle": {'mandatory': True, 'type': 'int'},
                         "socket_max_fail": {'mandatory': True, 'type': 'int'},
                         "master": {'mandatory': True, 'type': 'host'},
                         "port" :  {'mandatory' : True, 'type' : 'int'},
                     }
                }
    def __init__(self, bokor):
        """Bokor constructor

        @type  config: ConfigParser
        @param config: generated from cinegop2p.rc

        @return: Nothing
        """
        self.bokor = bokor
        self.socket = None
        self.stream = None
        self.check()

    def _init_socket(self) :
        """ _init_socket initialise self.socket

        @return; None
        """
        #socket creation
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # socket options
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        if (OS.startswith('CYGWIN')
            or OS == 'Darwin'):
            return

        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,
                               int(self.get("slave", "socket_idle", SOCKET_IDLE)))
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL,
                               int(self.get("slave", "socket_keep_alive", SOCKET_KEEP_ALIVE)))
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT,
                               int(self.get("slave", "socket_max_fail", SOCKET_MAX_FAIL)))


    def stop(self, status = 'quit'):
        self.exit_status = status
        self.exit = True

    def run(self):
        try:
            self._init_socket()
            self.exit = False
            self.exit_status = "reboot"
            master_host = self.get("slave", "master", MASTER_IP)
            master_port = self.get("slave", "port", MASTER_PORT)

            self.socket.connect((master_host, int(master_port)))
            self.stream = self.socket.makefile()
            logging.info("Connexion to master (%s:%s) succeed" %
                         (master_host, master_port))
            while True:
                if self.exit:
                    logging.info('closing interface unsafesocket')
                    break
                request = self.stream.readline().rstrip('\r\n')
                logging.debug('receive request : %s' % (request))
                if not request:
                    break
                request = json.loads(request)
                result = self.bokor.treat(Action(request['executor'], request['function'], request['params'], request['ressources']))
                logging.debug("answer at request : %s" % (result.global_answer))
                self.stream.write("%s\r\n" % json.dumps(result.global_answer))
                self.stream.flush()
            logging.error("Connection lost")
        except socket.error as v:
            logging.error("Cannot connect to a bokor Master : %s" % (v))
        finally:
            try :
                if self.socket :
                    self.socket.close()
                if self.stream :
                    self.stream.close()
            except :
                pass
            self.socket = None
            self.stream  = None
            
            return self.exit_status
