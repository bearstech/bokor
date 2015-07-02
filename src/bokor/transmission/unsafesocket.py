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

@file bokor/transmission/basetransmission.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief manage bokor peer and transmit order via socket
"""

from bokor.transmission.basetransmission import BaseTransmission
from bokor.constants.default import *

import gevent
import gevent.monkey
import gevent.pywsgi
import gevent.socket as socket
import string
import random
import logging
import sys

from bokor.transmission.plugins.unsafesocket.handler import Peer
from bokor.bocore.action import Action


class UnsafeSocket(BaseTransmission):

    configuration = {"master" :
                     {
                         "socket_keep_alive": {'mandatory': True, 'type': 'int'},
                         "socket_idle": {'mandatory': True, 'type': 'int'},
                         "socket_max_fail": {'mandatory': True, 'type': 'int'},
                         "ip" : {'mandatory' : True, 'type' : 'host'},
                         "port": {'mandatory' : True, 'type' : 'int'},
                     }
                 }
    def __init__(self, bokor):
        self.bokor = bokor
        self.check()
        self._init_socket()
        self.peers = []
        gevent.Greenlet(self).start()


    def _init_socket(self) :
        """ _init_socket initialise self.socket
        
        @return; None
        """
        #socket creation 
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # socket options
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,
                               int(self.get("master", "socket_idle", SOCKET_IDLE)))
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL,
                               int(self.get("master", "socket_keep_alive", SOCKET_KEEP_ALIVE)))
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT,
                               int(self.get("master", "socket_max_fail", SOCKET_MAX_FAIL)))

        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        #binding
        master_host = self.get("master", "ip", MASTER_IP)
        master_port = self.get("master", "port", MASTER_PORT)
        logging.debug("try to listen on %s(%s)"%(master_host, master_port))
        self.socket.bind((master_host, int(master_port)))
        self.socket.listen(64)
        self.timeout = int(self.get("master", "socket_timeout", SOCKET_TIMEOUT))



    def _transmit_to_peer(self, action, peer, timeout = None) :
        if not timeout :
            
            timeout = self.timeout
        if hasattr(action, 'timeout'):
            timeout = int(action.timeout)
        event = gevent.event.AsyncResult()
        action.event = event
        peer.push(action)
        return action.event.wait(timeout)        
        
    def transmit(self, action) :
        logging.debug("transmit %s(%s) for %s" % (action.function, action.executor, action.ressources))
        peers = self.get_peers(action, True)
        res = []
        for peer in peers:
            respeer = self._transmit_to_peer(action, peer)
            logging.debug("get response %s from : %s"%(respeer, peer))
            if respeer :
                res += respeer
            else:
                if peer not in action.timeouted :
                    action.timeouted.append(peer.token)
        return res



    def __id_generator(self) :
        tokens = [x.token for x in self.peers]
        while True :
            tmp_token = 'TMP' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(7))
            if tmp_token not in tokens : 
                return tmp_token

    def remove_peer(self, peer):
        self.peers.remove(peer)


    def validate_peer(self, peer) :
        #start communication with peer
        gevent.Greenlet(peer).start()
        #validate any peer enable to authenticate
        self._transmit_to_peer(Action(None, "auth", {}, []), peer, 15)
        if not peer.authed :
            return False
        if peer.status == 'unknown' :
            token_tmp = self.__id_generator()
            self._transmit_to_peer(Action(None, 'external_configuration', {'token_tmp' : token_tmp}, []), peer, 15)
            peer.token = token_tmp
        return True

    def __call__(self):
        """ __call__, function for greenlet management
        allow to receive new peer
        """
        while True:
            try:
                #   new connection 
                socket_peer, peername = self.socket.accept()
                # new peer
                peer = Peer(peername, socket_peer, self.bokor, self)
                if not self.validate_peer(peer) :
                    peer._close(False)
                self.peers.append(peer)
            except Exception as error:
                logging.error("exception %s in peer (%s) listen loop" %
                              (sys.exc_info(), self)) 
