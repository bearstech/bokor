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

@file interface/wsgi/view.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief view for pyramid wsgi server
"""

import logging
import json

from pyramid.view import view_config
from pyramid.config import Configurator

from bokor.bocore.action import Action

class View():

    """Class to define interface wsgi of bokor
    """

    def __init__(self, context, request):
        """View constructor

        @type  context: context
        @param context: pyramid context

        @type  request: dict
        @param request: pyramid request

        @return: none
        """
        self.request = request
        self.context = context
        self.acceptor = request.registry.settings['acceptor']


    def _get_ressources(self, params):
        ressources = []
        if 'token' in params:
            # is there a peer pricised in the resquest
            ressources = params.pop('token')
            if not isinstance(ressources, list) :
                ressources = [ressources]
        return ressources
        
    @view_config(route_name='bokor_simple', renderer='json')
    def simple(self):
        
        function = self.request.matchdict['function']
        params = self.request.params.mixed()
        ressources = []

        ressources = self._get_ressources(params)

        action = self.acceptor.treat(Action(None, function, params, ressources))
        return action.global_answer


    @view_config(route_name='bokor_executor', renderer='json')
    def withexecutor(self):
        executor = self.request.matchdict['executor']
        function = self.request.matchdict['function']
        params = self.request.params.mixed()
        ressources = []

        ressources = self._get_ressources(params)

        action = self.acceptor.treat(Action(executor, function, params, ressources))
        return action.global_answer

    @view_config(route_name='bokor_slash', renderer='json')
    def slash(self):
        action = self.acceptor.treat(Action(None, "slash", {}, []))
        return action.global_answer 



def routing(config):
    """Define defaults route for pyramid interface

    @type  config: ConfigParser executor
    @param config: configuration of cinego-p2p-server
    """
    logging.info('declaring routes for pyramid')

    # interfacing functions
    # with executor
    config.add_route('bokor_executor', '/{executor}.{function}{param:.*}')
    # with no executor
    config.add_route('bokor_simple', '/{function}{param:.*}')
    # specif case for / function
    config.add_route('bokor_slash', '/')


