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

@file bokor/bocore/action.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief action class
"""

from bokor.constants.error import *
import logging

class Action():
    """ Action is the intern representation of an order to bokor
    """
    
    def __init__(self, executor_name, function_name, params, ressources) :
        # executor : name of the wanted executor
        self.executor = executor_name

        # function : name of the wanted function
        self.function = function_name
        
        # params on the form of a dict {'key_name' : [values]}
        self.params = params

        # ressources is a list agent to whom the action is directed
        #an empty list is a "all with the function" alias
        self.ressources = ressources

        # results of the current agent
        self.results = None

        # return code of the current agent  
        self.code = NOT_TREATED

        # response of agents to which action was transmitted
        self.transmitted_answer = []

        # formatted answer of the agent sothing of the form
        #{"category": "bokor",
        # "answer": answer,
        # "code": 0,
        # "token_site":
        # "MASTERTOR",
        # "version": "1.0.0"}
        self.answer = []

        # shall this order be transmitted 
        self.transmit = True

        # shall this order be executed by this agent
        self.execute = True

        # shall this order be pre_treated by this agent
        self.pre = True

        # shall this order be post_treated by this agent
        self.post = True

        # the global answer, this agent's and the transmitted one in a list
        self.global_answer = []

        # flag for retro compatibility with cinepeer legacy
        self.legacy = False

        # list of unknown peers asked by this peer
        self.ghosts = []

        # list of peers that timmeouted
        self.timeouted = []

        #dynamic update on params :
        for key in self.params :
            if key.startswith('_bokor_') :
                value = self.params[key]
                if isinstance(value, basestring) and value.lower() == 'false' :
                    value = False
                if isinstance(value, basestring) and value.lower() == 'true' :
                    value = True
                setattr(self, key.replace('_bokor_', ''), value)

        self.bias()

    def bias(self) :
        # function to reimplement to bias an action for specific use
        pass
    
                
    def __repr__(self) :
        return str(self.__dict__)


    def _format_response(self, results, code, token, category, version) :
        answer = None
        if code == NOT_TREATED:
            logging.debug("action not treated")
        elif self.legacy :
            logging.debug("respect old formalism for answer")
            answer = {'token_site': token,
                      'function' : self.function,
                      'executor' : self.executor,
                      'category': category,
                      'code': code,
                      'answer': results,
                      'version': version,
            }
        else:
            logging.debug("new formalism for answer")
            answer = {'token': token,
                      'function' : self.function,
                      'executor' : self.executor,
                      'category': category,
                      'code': code,
                      'answer': results,
                      'version': version,
            }
        return answer
    
    def _get_global_answer(self):
        logging.debug("get global answer from %s", self)
        if self.answer:
            if self.transmitted_answer : 
                self.global_answer = [self.answer] + self.transmitted_answer
            else : 
                self.global_answer = [self.answer]
        elif self.transmitted_answer:
            self.global_answer = self.transmitted_answer
        else :
            self.global_answer = []

    def format_answer(self, token, category, version) :
        self.answer = self._format_response(self.results, self.code, token, category, version)
        for peer in self.ghosts :
            self.transmitted_answer.append(self._format_response("unknown peer : %s"%peer, UNKNOWN_PEER, peer, "unknown", "x.x.x"))
        for peer in self.timeouted :
            print "timeouted :", peer
            self.transmitted_answer.append(self._format_response("peer too slow to answer : %s"%peer, TIMEOUTED_PEER, peer, "unknown", "x.x.x"))

        self._get_global_answer()
            

        
