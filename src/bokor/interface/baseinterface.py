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

@file interface/interface.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief offer the listening loop by its run function
"""


import logging
from abc import ABCMeta
from abc import abstractmethod

from bokor.configuration.configurable import Configurable


class BaseInterface(Configurable):
    __metaclass__ = ABCMeta
    
    configuration = {"base" :
                     {"path_log": {'mandatory' : True, 'type' : 'file' , 'permission' : 'drwx', 'exist' : True}},
                 }
    
    dependances = { "configuration" : [] ,
                    "interface" : [],
                    "transmission" : [],
                    "feature" : []}



    def __init__(self, bokor):
        logging.error("init of BaseInterface, an abstract class")
        raise("BaseInterface is an abstract class")



    @abstractmethod
    def run(self) :
        pass

    @abstractmethod
    def stop(self) :
        pass


    def __repr__(self) :
        return "%s (Bokor Interface)" % (self.__class__.__name__)

