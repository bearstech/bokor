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

@file bokor.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief main class of bokor : Bokor, manage all object and the main loop
"""

import logging
import sys
import signal

from time import sleep

from constants.error import *
from configuration.baseconfiguration  import BaseConfiguration 
from interface.baseinterface import BaseInterface
from transmission.basetransmission import BaseTransmission
from executor.executor import Executor
from memory.basememory import BaseMemory
from bocore.bocore import Bocore
from bocore.action import Action


class Bokor():
    pass

def change_action(Act) :
    if issubclass(Act, Action) :
        Bokor.Action = Act


class Bokor():

    Action = Action

    def __init__(self, Configuration, Interface, Transmission, Features, Act = Action, handle_signal=True) :
        """Build Bokor object

        @type  Configuration: a subclass of the Configuration class 
        @param Configuration: Class that load, check and store the Configuration

        @type  Interface: a subclass of the Interface class 
        @param Interface: Class that manage the reception of order, its run function is the listening loop

        @type  Features: a list of subclass of the Feature class 
        @param Features: list of Class that process the order

        @type  Transmission: a subclass of the Transmission class 
        @param Transmission: Class that manage the connexion of other agent and transmit the orders to them

        @return: C_SUCCESS(=0)
        """
        change_action(Act)
        #init logging
        self._init_logging()
        self.bocore = None

        # deal with signals
        self.force_quit = False
        if handle_signal:
            signal.signal(signal.SIGTERM, self.quiting)
            signal.signal(signal.SIGINT, self.quiting)



        #try to create configuration
        configuration = self._init_configuration(Configuration)

        #configuration could be None, if the Configuration class
        #is not suitable.
        # in that case the _validate_classes will exist with a more global check.

        self._validate_classes(Configuration, Interface, Transmission, Features)

        # at this point all classes have the good type
        
        logging.info("All classes are of valid type")
        self._validate_dependance(Configuration, Interface, Transmission, Features)
        logging.info("All dependances are met")

        #after all validation configuration should not be empty
        # checking just in case

        if not configuration :
            logging.critical("configuration was not created, should not happen (sorry)")
            sys.exit(FATAL_ERROR)

        # ready to lauch
        self._launch(configuration, Configuration, Interface, Transmission, Features) 

        sys.exit(SUCCESS)

    def _init_logging(self):
        #logging.basicConfig(format='%(levelname)s:%(asctime)s:%(message)s',  level=logging.DEBUG)
        #logging instance
        self.logging =logging.getLogger()
        self.logging.setLevel(logging.DEBUG)
        #clean handlers :
        self.logging.handlers = []
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # create formatter
        formatter = logging.Formatter('%(levelname)s:%(asctime)s:%(filename)s:%(lineno)d:%(message)s')

        # add formatter to ch
        ch.setFormatter(formatter)
        # add ch to logger
        self.logging.addHandler(ch)
        
        #default logging handler, not known for the momment
        self.lh_stdout = ch

        

    def _launch(self, configuration, Configuration, Interface, Transmission, Features) :
        """ _launch create the bocore object and wait for it's return.
        At return Bocore objet will answer a set of classes, and a
        status tellling this function if this agent must be rebooter, reconfigured or stopped

        @type  configuration: class instance that load, check and store the Configuration
        @param configuration: the configuration object

        @type  Configuration: a subclass of the Configuration class 
        @param Configuration: Class that load, check and store the Configuration

        @type  Interface: a subclass of the Interface class 
        @param Interface: Class that manage the reception of order, its run function is the listening loop

        @type  Features: a list of subclass of the Feature class 
        @param Features: list of Class that process the order

        @type  Transmission: a subclass of the Transmission class 
        @param Transmission: Class that manage the connexion of other agent and transmit the orders to them

        @return nothing
        
        """



        #known object in a structure, that structure will be uses as return type par Bocore.run()
        original_bokor_struct = {'configuration_object' : configuration,
                                'Configuration' : Configuration,
                                'Interface' : Interface,
                                'interface_object' : None,
                                'Transmission' : Transmission,
                                'transmission_object' : None,
                                'Features' : Features,
                                'feature_object_list' : [],
                                'status' : 'init', #no bject instantiated exept configuration
                                }
        # we keep original and use bokor_struct
        logging.info("original structure for agent : %s" %
                     (str(original_bokor_struct)))
        bokor_struct = original_bokor_struct.copy()
        self.bocore = None

        # main loop
        while True :
            # creating only if needed 
            if not self.bocore : 
                logging.info("building bocore object")
                self.bocore = Bocore(configuration, Configuration, Interface, Transmission, Features)
            #running agent
            bokor_struct = self.bocore.run()
            #shall we quit ?
            if bokor_struct['status'] in ['quit'] or self.force_quit:
                self.bocore.destroy()
                break
            #shall we destroy Bocore ?
            # clodrebbot : destroy all then recreate
            if bokor_struct['status'] in ['coldreboot']:
                self.bocore.destroy()
                self.bocore = None

            sleep(15)
        return

    def _init_configuration(self, Configuration) :
        """ try to get logging from Configuration, if Configuration does not provide a logging
        _try_and_get_logging will configure stderr as logging
        
        @type  Configuration: a subclass of the Configuration class 
        @param Configuration: Class that load, check and store the Configuration

        return a Configuration instance, or None if not possible to instanciate Configuration, 
        """
        configuration = None
        valid_class = issubclass(Configuration, BaseConfiguration)
        if valid_class :
            configuration = Configuration()
            #if configuration is not ready (missing conf file) 
        self._try_and_get_logging(configuration)
        return configuration
        
    def _try_and_get_logging(self, configuration) :
        """ try to get logging from Configuration, if Configuration does not provide a logging
        _try_and_get_logging will configure stderr as logging
        
        @type  configuration: a subclass of the Configuration class 
        @param configuration: a Configuration object

        @return Nothing, 
        """
        new_handler = None
        
        if configuration :
            #we try to get the newhandler
            #
            new_handler = configuration.get_logging_handler()
        if new_handler :
            self.logging.debug("new handler %s for logging given by %s" % (new_handler, configuration))
            #rest handlers
            self.logging.handlers = []
            # installing the new handler
            self.logging.addHandler(new_handler)
            #setting new logging level
            self.logging.setLevel(new_handler.level)

        logging.info("logging ready")

        
        
        
        



    def _validate_dependance(self, Configuration, Interface, Transmission, Features) :
        """validate that all classes are meeting their dependances
        (class must be vlid before)
        
        @type  Configuration: a subclass of the Configuration class 
        @param Configuration: Class that load, check and store the Configuration

        @type  Interface: a subclass of the Interface class 
        @param Interface: Class that manage the reception of order, its run function is the listening loop

        @type  Features: a list of subclass of the Feature class 
        @param Features: list of Class that process the order

        @type  Transmission: a subclass of the Transmission class 
        @param Transmission: Class that manage the connexion of other agent and transmit the orders to them

        return : True if everything is valid
        """

        valid = True
        all_valid = True
        for bokorclass in [Configuration, Interface, Transmission] +  Features :
            #maybe it can be None
            if  bokorclass is None : continue
            for categorie, knowns in [("configuration", [Configuration]),
                                     ("interface", [Interface]),
                                     ("transmission", [Transmission]),
                                     ("feature", Features)] :
                for dclass in bokorclass.dependances[categorie] :
                    valid = False
                    for known in knowns :
                        if self._is_sub_class(known, dclass, log = False) :
                            valid = True
                    if not valid :
                        logging.critical("%s need of a %s for %s, but %s will be loaded" %
                                      (bokorclass, dclass, categorie,  str(knowns)))
                        all_valid = False

        if not all_valid :
            sys.exit(FATAL_ERROR)             


    def _validate_classes(self, Configuration, Interface, Transmission, Features) :
        """validate all clsses given as subclasses of the wanted class

        @type  Configuration: a subclass of the Configuration class 
        @param Configuration: Class that load, check and store the Configuration

        @type  Interface: a subclass of the Interface class 
        @param Interface: Class that manage the reception of order, its run function is the listening loop

        @type  Features: a list of subclass of the Feature class 
        @param Features: list of Class that process the order

        @type  Transmission: a subclass of the Transmission class 
        @param Transmission: Class that manage the connexion of other agent and transmit the orders to them

        return : Nothing, quit if not validate
        """
        
        valid = self._is_sub_class(Configuration, BaseConfiguration) 
        valid = self._is_sub_class(Interface, BaseInterface) and valid
        valid = self._is_sub_class(Transmission, BaseTransmission, allow_none = True) and valid
        valid = reduce(lambda x,y: x and y,
                       [ self._is_sub_class(Feature, Executor)
                         for Feature in Features], True) and valid
        if not valid : 
            logging.error("Classes misfit, aborting")
            sys.exit(FATAL_ERROR) 


    def _is_sub_class(self, wanted, mandatory, allow_none = False, log = True) :
        """validate that wanted is a sub class of mandatory

        @type  wanted: a class wanted
        @param wanted: the class to test

        @type  mandatory: a class
        @param mandatory: the class that wanted should heritated from

        return True if wanted is a sub class of mandatory, False in any other case
        """
        try :
            #are we allowing None and is it None as wanted
            if allow_none and not wanted :
                return True
            if not issubclass(wanted, mandatory) :
                if log : 
                    logging.error(
                        "%s is not a sub Class of %s" %
                        (wanted.__name__, mandatory.__name__))
                return False
            return True
        except TypeError :
            if log :
                logging.error(
                    "%s is not a Class but a %s (awaiting a sub class of %s)" %
                    (str(wanted), type(wanted), mandatory.__name__))
        return False


    def quiting(self, signal, frame) :
        logging.critical('Caught signal %s, exiting.' % (str(signal)))
        self.force_quit = True
        self.bocore.interface.stop('quit')
        sys.exit()
