#! /usr/bin/env python

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
@brief handle peer connection
"""
import gevent.socket as socket
import gevent.queue as gqueue
import gevent.event
import gevent.coros as gcoros
import json
import logging
import sys
import re

from bokor.constants.error import *
from bokor.bocore.action import Action
from bokor.constants.default import *

class Peer():

    def __init__(self, peername, socket_peer, bokor, pool):
        self.bokor = bokor
        self.socket = socket_peer
        self.ip, self.port = peername
        self.token = None
        self._init_socket()
        self.stream = self.socket.makefile()
        self.queue = gqueue.Queue()
        self.lock = gcoros.Semaphore()
        self.pool = pool
        self.closed = True
        self.status = 'unknown'
        self.misfit = {}
        self.authed = False
        self.actions = []
        self.version = "x.x.x"
        self.category = "unknown"
        
    def _init_socket(self) :
        """ _init_socket initialise self.socket
        
        @return; None
        """
        # socket options
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,
                               int(self.bokor.get("master", "socket_idle", SOCKET_IDLE)))
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL,
                               int(self.bokor.get("master", "socket_keep_alive", SOCKET_KEEP_ALIVE)))
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT,
                               int(self.bokor.get("master", "socket_max_fail", SOCKET_MAX_FAIL)))

        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)



    def push(self, action):
        #push a message to the peer queue
        self.queue.put((action))

    def __msg_handler(self):
        #main loop to send messages to the peer
        while True:
            try:
                #get last message from the queue, blocking call
                logging.debug("wating message for %s"%self.token)
                action = self.queue.get()
                self.actions.append(action)
                if action is None:
                    # message is none, ending
                    logging.debug('message is none, exiting forn main sending loop')
                    continue
                try:
                    # send to peer
                    logging.debug("sending to %s"%self.token)
                    self.stream.write("%s\r\n" % json.dumps(
                        dict(executor=action.executor,
                             ressources=action.ressources,
                             function=action.function,
                             params=action.params)))
                    self.stream.flush()
                except IOError:
                    logging.error("IO error in message sending loop")
                    self.actions = []
                    self._close()
                    raise
            except Exception as error:
                self.actions = []
                self._close()
                logging.error("exception %s in peer (%s) message sending loop" %
                              (sys.exc_info(), self))
        
    def __call__(self):
        """ __call__, function for greenlet management of peer
        """
        msghandler = gevent.Greenlet(self.__msg_handler)
        msghandler.start()
        #main loop to get answer from the peer
        try:
            while True:
                try:
                    #is there data in the stream from the peer
                    result = self.stream.readline().rstrip('\r\n')
                    logging.debug('get result from %s'%self.token)
                except IOError:
                    logging.ERROR('IOERROR in getting response from %s, closing'%self.token)
                    self._close()
                    break
                if not result :
                    logging.ERROR('getting empty response from %s, closing'%self.token)
                    self._close()
                    break
                result = json.loads(result)
                logging.debug("get result : %s "% result)
                # FIXME RETRO /!\ B
                #
                if not isinstance(result, list):
                    result = [result]
                # FIXME RETRO /!\ E
                


                if result and not self.authed : 
                    #specific case of auth, we don't know if it's an auth, but it's the first request
                    self._auth(result[0])
                    self.authed = True
                action = self.actions.pop(0) # FIFO
                action.transmitted_answer = result
                action.event.set(action.transmitted_answer)
                self.actions = []
        except Exception as error:
            logging.error("exception %s in peer (%s) listen loop" %
                          (sys.exc_info(), self))
        finally:
            logging.info("%s no more connected" % self)
            msghandler.kill()        
            self._close()

    def _auth(self, result) :

        #FIXME RETRO /!\ B
        # we change the result format if version is < 0
        if result['version'].startswith("0") :
            tok = result['answer']
            result['answer'] = {'token' : tok}
            for key in result['infos'] :
                nkey = key
                if key == 'conf_error' :
                    nkey = 'misfit'
                result['answer'][nkey] = result['infos'][key]
        #FIXME RETRO /!\ E
        if result["code"] != AUTH:
            # if it was not an auth function :
            self.misfit["auth"] = "No valid auth function" 
        else :
            if isinstance(result['answer'], dict) :
                #should be true
                self.__dict__.update(result['answer'])
        self.category = result['category']
        self.version = result['version']


        if self.misfit :
            self.status = 'faulty'
        elif self.token and not re.match("^00*$", self.token) :
            self.status = 'ready'
            
        
        
    def _close(self, close = True):
        try :
            if close : 
                self.pool.remove_peer(self)
        except Exception as error:
            err = str(sys.exc_info())
            logging.error("exception peer not known in list peers %s" % (err))        
        with self.lock:
            for action in self.actions :
                action.transmitted_answer = []
            try:
                self.socket.close()
            except Exception as error:
                err = str(sys.exc_info())
                logging.error("exception on socket close %s" % (err))
            try:
                self.stream.close()
            except Exception as error:
                err = str(sys.exc_info())
                logging.error("exception on stream close %s" % (err))
            finally:
                self.closed = True
            self.queue.put(None)


    def __str__(self) :
        return str({'token' : self.token, 'ip' : self.ip , 'status' : self.status})
            
