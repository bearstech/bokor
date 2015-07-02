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

@file interface/wsgi.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief offer an interface as a wsgi service
"""

from pyramid.config import Configurator
import gevent.pywsgi
import signal

import logging

from bokor.interface.baseinterface import BaseInterface
from bokor.interface.plugins.wsgi.view import routing, View
from bokor.interface.plugins import wsgi


class WSGI(BaseInterface):

    needed_configuration = {"wsgi" :
                     {"ip": {'mandatory' : True, 'type' : 'host'},
                      "port": {'mandatory' : True, 'type' : 'int'},
                  }
                 }
    
    dependances = { "configuration" : [] ,
                    "interface" : [],
                    "transmission" : [],
                    "feature" : []}

    

    def __init__(self, bokor):
        """ init WSGI interface thru Pyramid
        """
        logging.info("init of wsgi interface")
        self.bokor = bokor
        self.exit_status = "quit"
        self.settings = {}
        self.settings['reload_all'] = False
        self.settings['debug_all'] = True

        self.wsgi_config = Configurator(settings=self.settings)
        self._get_routes()

        self.wsgi_config.registry.settings['acceptor'] = self.bokor

        self.application = self.wsgi_config.make_wsgi_app()
        self.check()


    def _get_routes(self) :
        self.wsgi_config.scan(wsgi)
        routing(self.wsgi_config)
        
    def run(self) :
        self.server = gevent.pywsgi.WSGIServer((self.get('wsgi', 'ip', '0.0.0.0'),
                                               int(self.get('wsgi', 'port', '4444'))),
                                      self.application)
        gevent.signal(signal.SIGTERM, self.stop)
        self.server.serve_forever()
        return self.exit_status
        


    def stop(self, status = 'quit'):
        self.status = status
        self.server.stop()



           

    
