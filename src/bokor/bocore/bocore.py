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

@file bokor/bocore/bocore.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief core code of bokor
"""

import logging
import json
import copy
import time
import traceback
import sys

from bokor.executor.executor import Executor, aFeature, anExecutor, aPreProcess
from bokor.constants.error import *
from bokor.configuration.configurable import Configurable
from bokor.interface.unsafesocket import UnsafeSocketClient


VERSION = '1.0.7'

@anExecutor
class Bocore(Configurable):


    emergency_interface = UnsafeSocketClient

    needed_configuration = {"bokor":
                            {"token"   : {'mandatory': True, 'type': 'string'},
                             "category": {'mandatory' : False, 'type' : 'string'},}
                        }

    def __init__(self, configuration, Configuration,
                 Interface, Transmission, Features):
        """ core class of bokor
        @type  configuration: class instance that load,
        check and store the Configuration
        @param configuration: the configuration object

        @type  Configuration: a subclass of the Configuration class
        @param Configuration: load, check and store the Configuration

        @type  Interface: a subclass of the Interface class
        @param Interface: manage the reception of order,
        its run function is the listening loop

        @type  Features: a list of subclass of the Feature class
        @param Features: list of Class that process the order

        @type  Transmission: a subclass of the Transmission class
        @param Transmission: manage the connexion of other agent
        and transmit the orders to them

        """
        # for heriting purpose
        self.bokor = self
        Executor.bokor = self
        #reread conf
        configuration.load_conf_file()
        self.executors = {}
        self.misfit_general = {}
        self.bokor_struct = {'configuration_object': configuration,
                             'Configuration': Configuration,
                             'Interface': Interface,
                             'interface_object': None,
                             'Transmission': Transmission,
                             'transmission_object': None,
                             'Features': Features,
                             'feature_object_list': [],
                             # no object instantiated exept configuration
                             'status': 'init',
                             }

        # keeping classes
        self.configuration_class = Configuration
        self.interface_class = Interface
        self.features_classes = Features
        self.transmission_class = Transmission

        # building object needed
        # we already have a configuration
        self.configuration = configuration
        self._validate_object(self.configuration)

        # self checking
        self.check()

        self.token = self.get("bokor", "token", "00000000")
        self.category = self.get("bokor", "category", "Bokor")
        self.version = VERSION

        if self._validate_class(Interface) :
            #if interface properly configurated ;
            # we create it
            logging.debug("interface valid, implementing")
            self.interface = Interface(self)
        else:
            #we implente a emergency connection
            logging.error("unvalid interface using emergency %s" %  self.emergency_interface)
            self.interface = self.emergency_interface(self)
        self._validate_object(self.interface)

        # transmission can be None
        if Transmission and self._validate_class(Transmission):
            logging.debug("Crestion of %s instance" % Transmission)
            self.transmission = Transmission(self)
            self._validate_object(self.transmission)
        else:
            self.transmission = None

        self.features = []
        for F in Features :
            if self._validate_class(F) :
                f = F(self)
                self.features.append(f)
                self._validate_object(f)

        # self features
        self._update_executors(self)
        print str(self.token) + '(' + self.version + ') : connection succeed'
        logging.error("Bocore ready")


    def get_executor(self, name) :
        for executor in self.executors :
            print executor, name
            if executor == name :
                return self.executors[executor]['objt']
        return None

    def _get_function_to_call(self, fun_name,
                              class_name=None, table='features', prefix=''):
        """given a function name, give the executor name, object and function
        with this name it can be use to search feature preprocess ou
        postprocess

        @type  fun_name: string
        @param fun_name: name of the function we search

        @type  class_name : string
        @param class_name : name of the executor, if None,
        match fun_name against all executors known

        @type  table : string
        @param table : table in witch to search the function
        ('features', 'preprocessing' or 'postprocessing'

        @type  prefix: string
        @param prefix: allowed prefix,
        search of hello with 'pre' as prefix will hit hello, prehello
        or pre_hello

        @return : exe, fun, objt for : exe the executor name,
        fun the methode and objt the executor object

        """

        fun = None
        exe = None
        objt = None
        # all executor possible
        executors = self.executors
        # if the executor name is given, we limit to it (if it exist,
        # otherwise, executors = []
        if class_name:
            executors = {}
            for x in self.executors.keys():
                if class_name.lower() == x.lower():
                    executors[x] = self.executors[x]

        # search in executors
        for executor in executors:
            finded = False
            if fun_name in self.executors[executor][table]:
                finded = True

            # if no candidate but a prefix allowed
            if not finded and prefix:
                # we try to find a function name prefixName
                if prefix + fun_name in self.executors[executor][table]:
                    fun_name = prefix + fun_name
                    finded = True
                elif (prefix + '_' + fun_name
                      in self.executors[executor][table]):
                    fun_name = prefix + '_' + fun_name
                    finded = True

            # store answer and break
            if finded:
                fun = self.executors[executor][table][fun_name]['function']
                exe = executor
                objt = self.executors[executor]['objt']
                break

        return exe, fun, objt

    def _validate_class(self, cls):
        """validate a class feature : check if class is correctly configured.
        if not don't instanciate it, else instanciate an put in self.features

        @type  objt: object
        @parma objt: object to validate

        @return : True if the object is valid, False otherwise

        """
        logging.debug("validating class %s" % (cls))
        checked, misfit = self.configuration.check(cls)
        logging.debug("validating class %s : checked %s " % (cls, checked))

        if misfit :
            logging.error("%s not valid" % cls)
            self._update_misfit(misfit)
            return False
        return True


    def _validate_object(self, objt):
        """validate an object : check if is_ready, update_executors if needed
        and update self.misfit_general if needed

        @type  objt: object
        @parma objt: object to validate

        @return : True if the object is valid, False otherwise

        """
        logging.debug("validating %s" %
                      (objt))
        if not objt.checked :
            logging.info("%s is not checked"%
                      (objt.__class__.__name__ ))
            objt.check()
        if objt.is_ready():
            logging.debug("%s ready" %
                          (objt))
            if isinstance(objt, Executor):
                # if objt is an executor
                self._update_executors(objt)
            return True
        logging.error("%s not ready" %
                      (objt))
        return False

    def _update_misfit(self, misfit):
        # update general misfit
        for section in misfit:
            if section not in self.misfit_general:
                self.misfit_general[section] = {}
            for option in misfit[section]:
                if option not in self.misfit_general[section]:
                    self.misfit_general[
                        section][option] = misfit[section][option]
        return False

    def _update_executors(self, objt):
        """ updates executors functions table, feature pre and postprocessing

        @type  objt: an Executor offspring
        @param objt; the executor we want to know

        @return : None
        """
        logging.debug("update executor %s" % (objt))
        class_name = objt.__class__.__name__
        # if it's bocore as an executor we call it bokor
        if class_name == 'Bocore':
            class_name = 'Bokor'
        # updating
        self.executors[class_name] = {'objt': objt,
                                      'features': objt.get_features(),
                                      'preprocess': objt.get_preprocess(),
                                      'postprocess': objt.get_postprocess()}

    # entry point
    def treat(self, action):
        """treat is the entry point for the interface

        @type  action: an Action, cf bokor.bocore.action
        @param action; the action representing the ordre to bokor

        @return : an action with the anxwer in it
        """
        try:
            logging.debug("treating %s ( %s ) for %s :" %
                          (action.function, action.params, action.ressources))

            # pre treating the action if action allow it
            if action.pre :
                action = self.__pretreat(action)

            # if this agent is targeted by the action and autorized to do it:
            if action.execute and (action.ressources == [] or self.token in action.ressources):
                if action.ressources :
                    action.ressources.remove(self.token)
                    #is the list empty now ?
                    if not action.ressources :
                        #if yes no more transmission
                        action.transmit = False
                # the results fieald will be updated
                self.__call(action)


            # if we need to transmit
            if self.transmission and action.transmit:
                action.transmitted_answer = self.transmission.transmit(action)

            # post treating action if action allow it
            if action.post :
                action = self.__posttreat(action)
            #fromatting answer of the agent
            action.format_answer(self.token, self.category, self.version)
        except Exception as e:
            logging.error("exception : %s , %s"%(str(e), traceback.format_tb(sys.exc_info()[2])))
            action.code = UNEXCEPTED_EXCEPTION
            res = {}
            res["error"] = str(e)
            res["type"] = "%s.%s" % (type(e).__module__, type(e).__name__)
            res["traceback"] = traceback.format_tb(sys.exc_info()[2])
            action.results = res
            action.format_answer(self.token, self.category, self.version)
        return action

    def __pretreat(self, action):
        """ __pretreat execute pretreatment if a suitable preprocessing is available

        @type  action: an Action, cf bokor.bocore.action
        @param action; the action representing the ordre to bokor

        @return : an action
        """

        exe, fun, objt = self._get_function_to_call(
            action.function, action.executor, 'preprocess', 'pre')
        logging.debug("searching pretreatment for %s.%s, get %s" %
                      (action.executor, action.function, fun))
        # no preprocessing
        if not fun:
            return action
        new_action = fun(objt, action)
        return new_action

    def __posttreat(self, action):
        """ __postreat execute posttreatment if a suitable postprocessing is available

        @type  action: an Action, cf bokor.bocore.action
        @param action; the action representing the ordre to bokor

        @return : an action
        """
        exe, fun, objt = self._get_function_to_call(
            action.function, action.executor, 'postprocess', 'post')
        logging.debug("searching posttreatment for %s.%s, get %s" %
                      (action.executor, action.function, fun))

        # no postprocessing
        if not fun:
            return action
        new_action = fun(objt, action)
        return new_action

    def __call(self, action):
        """ call allow to find and call a feature given an action

        @type  action: an Action, cf bokor.bocore.action
        @param action; the action representing the ordre to bokor

        @return : None
        """

        exe, fun, objt = self._get_function_to_call(
            action.function, action.executor)
        if exe :
            action.executor = exe
        # no feature known for that action
        logging.debug("searching feature for %s.%s, get %s" %
                      (action.executor, action.function, fun))

        if not fun:
            logging.debug("no feature for action ; %s" % (action))
            if not action.executor:
                action.code = FUNCTION_UNKNOWN
                action.results = "function %s unknown" % (action.function)
            else:
                action.code = FUNCTION_UNKNOWN
                action.results = "function %s.%s unknown" % (
                    action.executor, action.function)
            return

        # building args
        args = {}
        # mandatory
        for arg in self.executors[exe]['features'][
                action.function]['mandatory']:
            if arg == 'self':
                # specific case for self
                args['self'] = objt
                continue
            if arg not in action.params:
                # error of mandatory param
                logging.debug("%s mandatory" % (arg))
                action.code = MANDATORY_MISSING
                action.results = "%s is mandatory" % (arg)
                return
            value = action.params[arg]
            args[arg] = value

        # optional
        for arg in self.executors[exe]['features'][
                action.function]['optional']:
            if arg in action.params:
                value = action.params[arg]
                if len(value) == 1:
                    value = value[0]
                args[arg] = value

        # call the fun
        res = fun(**args)
        # save return code
        action.code = fun.code
        # save results
        action.results = res



    def run(self):
        """ run launch the bokor agent
        @return a stucture of kokor configuration :

        {'configuration_object' : configuration,
        'Configuration' : Configuration,
        'Interface' : Interface,
        'interface_object' : None,
        'Transmission' : Transmission,
        'transmission_object' : None,
        'Features' : Features,
        'feature_object_list' : [],
        'status' : 'init',
        }

        """
        logging.debug("bocore running")

        # launch interface
        self.bokor_struct['status'] = self.interface.run()

        # interface let go ; we can quit
        if not self.bokor_struct['status'] :
            self.bokor_struct['status'] = 'quit'

        logging.debug("Bocore run exit with status : %s" %
                      (self.bokor_struct['status']))
        return self.bokor_struct

    def destroy(self):
        """ destroy function
        """
        logging.debug('bocore destroy called')
        self.interface.stop()
        [ f.shutdown() for f in self.features ]

    @aPreProcess
    def pre_get_misfit(self, action):
        action.execute = True
        return action

    @aFeature
    def get_misfit(self):
        return self.misfit_general


    @aPreProcess
    def pre_quit(self, action):
        if self.token in action.ressources :
            action.transmit = False
            action.execute = True
        else :
            action.execute = False
        return action





    @aFeature
    def quit(self):
        """ quit : order bokor to shutdown

        """
        logging.info("bokor quit")
        self.interface.stop()
        return True

    @aPreProcess
    def pre_reboot(self, action):
        """ reboot : reboot bokor agent
        """
        if self.token in action.ressources :
            action.transmit = False
            action.execute = True
        else :
            action.execute = False
        return action



    @aFeature
    def reboot(self, cold = False):
        """ quit : order bokor to shutdown

        @type  msg: string
        @param msg: reason of quitting
        """
        logging.info("bokor reboot : cold = %s" %
                     (cold))
        status = 'reboot'
        if cold :
            status = 'coldreboot'
        self.interface.stop(status)
        return True



    @aPreProcess
    def pre_help(self, action):
        action.execute = True
        return action


    @aFeature
    def hold(self, delta):
        print "hold", delta
        time.sleep(int(delta))
        return delta


    @aFeature
    def help(self, table = 'features', executor = None):
        """ main help function
        @return : a dictionnaire of all executor and feature available
        """
        wanted = executor
        res = {}
        if not table in ['features', 'preprocess', 'postprocess']:
            table = 'features'
        for executor in self.executors:
            if wanted :
                if wanted != executor :
                    continue

            res[executor] = {}
            for feature in self.executors[executor][table]:
                mandatory = self.executors[executor][
                    table][feature]['mandatory']
                res[executor][feature] = {
                    'mandatory': copy.copy(self.executors[executor][
                        table][feature]['mandatory']),
                    'defaults': copy.copy(self.executors[executor][
                        table][feature]['defaults']),
                    'doc': copy.copy(self.executors[executor][
                        table][feature]['doc']), }
                #we don't want to show 'self'
                if 'self' in res[executor][feature]['mandatory']:
                    res[executor][feature]['mandatory'].remove('self')

        return res


    @aPreProcess
    def pre_auth(self, action) :
        """preauth block transmission of an auth order if this order is for
        the current bokor agent
        """
        if self.token in action.ressources or action.ressources == [] :
            action.transmit = False
        return action
