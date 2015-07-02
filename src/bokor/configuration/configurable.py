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
@brief configurble class, a class that can be configured
"""


class Configurable(object) :

    conf_ready = False
    checked = False
    misfit = None
    bokor = None

    needed_configuration = {}

    def check(self):
        """ check the configuration thru a self.bokor.
        
        @type  object : any object 
        @param object : an object with a configuration dictionnary
        
        return a couple (bool, misfit)
        bool is true if the check take place
        misfit is the list of problematique configuration 
        """
        if self.bokor :
            self.checked, self.misfit = self.bokor.configuration.check(self)

        self.configurated = (self.misfit == {})
        self.conf_ready = self.checked and self.configurated



    def is_ready(self) :
        return self.conf_ready

    
    def is_checked(self) :
        return self.checked

    def get_misfit(self):
        return self.misfit

    def get(self, section, option, default = None):
        if self.bokor :
            return self.bokor.configuration.get(section, option, default)
        return default
