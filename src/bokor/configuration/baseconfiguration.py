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

@file configuration/configuration.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief base configuration class for bokor
"""

import logging
import os
import ConfigParser

from checker import ConfigChecker
from configurable import Configurable

from bokor.executor.executor import Executor, aFeature, anExecutor, aPreProcess
from bokor.constants.error import *

@anExecutor
class BaseConfiguration(Configurable):

    conf_file = "~/.config/bokor.rc"

    needed_configuration = { "logging" :
                      {
                          "path": {'mandatory' : True, 'type' : 'file' , 'permission' : 'rw', 'exist' : False},
                          "level" : {'mandatory': False, 'type': 'string'},
                      }
                  }

    dependances = { "configuration" : [] ,
                    "interface" : [],
                    "transmission" : [],
                    "feature" : []}
    _config = None
    _checker = ConfigChecker()
    handler = None
    file_handler = None

    
    def __init__(self):
        self.load_conf_file()
        self.checked, self.misfit = self.check(self)
        # a configuration can work without configuration
        # it's checked and ready by construction
        self.configurated = (self.misfit == {})
        self.conf_ready = True
        self.checked = True
        
        if not self.is_ready() :
            logging.warn("%s not ready : checked = %s, configurated = %s" %
                         (self, self.checked, self.is_ready()))



    def get_log_file(self):
        return self.file_handler
            
            

    def get_logging_handler(self) :
        """ configure logging
        return Nothing
        """
        if not self.is_ready() :
            logging.warn("call get_logging_handler on a not ready configuration")
            return None
        if not self.handler :
            if self.get("logging", "path", "") != "" :
                self.file_handler = os.path.expanduser(self.get("logging", "path"))
            if not self.file_handler :
                return None
            logging.debug("logging to %s" % (self.file_handler)) 
            #we keep only the file descriptor
            self.handler = open(self.file_handler, "w")

        #creating streamhandler
        new_handler = logging.StreamHandler(self.handler)
        # formating new handler
        new_handler.setFormatter(logging.Formatter('%(levelname)s:%(asctime)s:%(filename)s:%(lineno)d:%(message)s'))
        asked_level = self.get("logging", "level", "DEBUG")

        # configure level
        level = self._get_log_levels(asked_level)
        new_handler.setLevel(level)
        return new_handler

    def _get_log_levels(self, asked) :
        """ return a logging level from a string
        
        @type asked : string (the function is case unsensitive)
        @aram asked : string that should represent a level

        @return : a logging level corresponding to the string, if possible, logging.DEBUG otherwise
        """

        level = logging.DEBUG
        level_string = "debug"
        known_levels = { "debug" : logging.DEBUG,
                         "info" : logging.INFO,
                         "warning" : logging.WARNING,
                         "error": logging.ERROR,
                         "critical" : logging.CRITICAL, }

        # to lower 
        lasked = asked.lower()

        if lasked in known_levels :
            level = known_levels[lasked]
            level_string = lasked
            
        logging.debug("logging level : %s" % (level_string.upper()))
        return level

    def load_conf_file(self):
        """load configuration from file
        
        return : nothing
        """
        # make sur to have absolute path
        self.conf_file = os.path.realpath(os.path.expanduser(self.conf_file))
        if not os.path.isfile(self.conf_file) :
            logging.error("configuration file : %s doesn't not exist" %
                          (self.conf_file))
            return
        if not self._config : 
            self._config = ConfigParser.ConfigParser()
        config_fp = open(self.conf_file, 'r')
        self._config.readfp(config_fp)
        config_fp.close()


    
        

    def get(self, section, option, default = None) :
        if not self._config :
            logging.error("call of configuration.get but no conf is loaded")
            return default
            
        if not self._config.has_section(section) :
            logging.error("configuration : call for value of (%s, %s), but %s is not a section" %
                         (section, option, section))
            return default
        if not self._config.has_option(section, option) :
            logging.error("configuration : call for value of (%s, %s), but %s is not an option" %
                         (section, option, option))
            return default

        value = self._config.get(section, option)
        logging.debug("(%s, %s) = %s" %
                     (section, option, value))
        return value
        
        
    def check(self, object):
        """ check the configuration needed by an object
        
        @type  object : any object 
        @param object : an object with a configuration dictionnary
        
        return a couple (bool, misfit)
        bool is true if the check take place
        misfit is the list of problematique configuration 
        """
        logging.debug("checking configuration of %s" %
                     (object))
        if not self._config :
            logging.error("call of configuration.check but no conf is loaded")
            return False, {}

        if not hasattr(object, "needed_configuration"):
            logging.info("call of configuration.check on a class without configuration attribute : " %
                          (str(object)))
            return True, {}


        if not object.needed_configuration :
            misfit = {}
        else :
            misfit = self._checker.check_conf(object.needed_configuration, self._config)

        if (misfit == {}):
            logging.debug("Configuration for %s is valid" %
                         (object))
            return True, misfit


        logging.debug("Configuration for %s is not valid, misfit : %s" %
                      (object, misfit))
        return True, misfit
    

        
        
    def __del__(self):
        if self.handler : 
            self.handler.close()


    def __repr__(self) :
        return "%s (Bokor Configuration)" % (self.__class__.__name__)


    # features :

    @aFeature
    def get_conf(self, section = None, option = None) :
        if (option and not section) :
            self._bokor_code = MANDATORY_MISSING
            return "section is mandatory if you give an option"

        if not self._config :
            self._bokor_code = NO_CONF
            return "No conf file was loaded"

        if not section and not option :
            res = {}
            for s in self._config.sections():
                res[s] = {}
                for o in self._config.options(s):
                    res[s][o] = self._config.get(s, o)
            return res
        
        if not self._config.has_section(section) :
            self._bokor_code = VALUE_UNFIT
            return "%s is not a section"%section

        if not option :
            res = {}
            for o in self._config.options(section):
                res[o] = self._config.get(section, o)
            return res
        if not self._config.has_option(section, option) :
            self._bokor_code = VALUE_UNFIT
            return "%s is not an option of %s"%(option, section)

        return self._config.get(section, option)

        
    @aFeature
    def set_conf(self, section, option, value) :
        if not self._config.has_section(section) :
            logging.error("try to set value of (%s, %s), but %s is not a section" %
                         (section, option, section))
            self._bokor_code = VALUE_UNFIT
            return "%s is not a section"%section

        self._config.set(section, option, value)
        return True


    @aFeature
    def write_conf(self):
        config_fp = open(self.conf_file, 'w')
        self._config.write(config_fp)
        config_fp.close()   
        return True


    @aFeature
    def create_section(self, section) :
        if not self._config :
            self._bokor_code = NO_CONF
            return "No conf file was loaded"
        self._config.add_section(section)
        return True

    @aFeature
    def remove_option(self, section, option):
        if not self._config.has_section(section) :
            logging.error("try to remove (%s, %s), but %s is not a section" %
                          (section, option, section))
            self._bokor_code = VALUE_UNFIT
            return "%s is not a section"%section
        if not self._config.has_option(section, option) :
            logging.error("try to remove (%s, %s), but %s is not an option" %
                          (section, option, option))
            self._bokor_code = VALUE_UNFIT
            return "%s is not an option"%option
        self._config.remove_option(section, option)

    @aFeature
    def remove_section(self, section):
        if not self._config.has_section(section) :
            logging.error("try to remove %s, but it doesn't exist" %
                          (section))
            self._bokor_code = VALUE_UNFIT
            return "%s is not a section"%section
        self._config.remove_section(section)
        
