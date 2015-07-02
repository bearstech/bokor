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
@brief action dedicated to rtorrent management
"""


from bokor.bocore.action import Action
from bokor.constants.error import *
import logging

class STAction(Action) :
    #Slave Torrent action 
    def bias(self):
        self.legacy = True


class STActionLegacy(Action) :
    # Slave torrent action legacy style
    def bias(self) :
        self.legacy = True

    def _format_response(self, results, code, token, category, version) :
        answer = None
        if code == NOT_TREATED:
            logging.debug("action not treated")
            return answer
        logging.debug("respect old formalism for answer")
        answer = {'token_site': token,
                  'function' : self.function,
                  'executor' : self.executor,
                  'category': category,
                  'code': code,
                  'answer': results,
                  'version': version,
              }
        return answer

class MTAction(Action) :
    #Slave Torrent action 
    def bias(self):
        self.execute = False
        self.legacy = True


class MTActionLegacy(Action) :
    # Slave torrent action legacy style
    def bias(self) :
        self.execute = False
        self.legacy = True

    def _format_response(self, results, code, token, category, version) :
        answer = None
        if code == NOT_TREATED:
            logging.debug("action not treated")
            return answer
        logging.debug("respect old formalism for answer")
        answer = {'token_site': token,
                  'function' : self.function,
                  'executor' : self.executor,
                  'category': category,
                  'code': code,
                  'answer': results,
                  'version': version,
              }
        return answer
