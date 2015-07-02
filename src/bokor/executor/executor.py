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

@file feature/feature.py
@author Olivier ANDRE <zitune@bearstech.com> 
@author Maurice AUDIN <maudin@bearstech.com>
@date 2014
@brief call management
"""

import copy
import inspect
import sys
import traceback
import logging
from bokor.bocore.action import Action
from bokor.configuration.configurable import Configurable
from bokor.constants.error import *


#feature decorator
def aFeature(f) :
    def wrapper( self, *args, **kwargs):
        #init return to SUCCESS
        self._bokor_code = SUCCESS
        try:
            res = f(self, *args, **kwargs)
        except Exception as e:
            print "exception from wrapper", f.func_name, str(e)
            self._bokor_code = UNEXCEPTED_EXCEPTION
            if self.return_codes.has_key(type(e)):
                self._bokor_code = self.return_codes[type(e)]
            logging.error(type(e).__module__, type(e).__name__)
            logging.error(traceback.format_tb(sys.exc_info()[2]))
            res = {}
            res["error"] = str(e)
            if self.get("logging", "level", "debug") == "debug":
                res["type"] = "%s.%s" % (type(e).__module__, type(e).__name__)
                res["traceback"] = traceback.format_tb(sys.exc_info()[2])
        wrapper.code = self._bokor_code
        return res
    aFeature.table[f.func_name] = {'function' : wrapper,
                                   'mandatory' : [],
                                   'optional' : {},
                                   'defaults' : {},
                                   'doc' : '',
                                   'original_func' : f}
    all_p = inspect.getargspec(f).args
    optional_value = inspect.getargspec(f).defaults
    if optional_value :
        nb_optional = len(optional_value)
        aFeature.table[f.func_name]['mandatory'] = all_p[:-nb_optional]
        aFeature.table[f.func_name]['optional'] = all_p[-nb_optional:]
        aFeature.table[f.func_name]['defaults'] = dict(zip(all_p[-nb_optional:], optional_value))
    else :
        aFeature.table[f.func_name]['mandatory'] = all_p
        aFeature.table[f.func_name]['optional'] = []
    doc = inspect.getdoc(f)
    if doc :
        aFeature.table[f.func_name]['doc'] = inspect.cleandoc(doc)

    return wrapper

aFeature.table = {}




#preprocessing decorator
def aPreProcess(f) :
    def wrapper(self, action) :
        old_action = action
        #pass it by copy
        action = f(self, copy.copy(action))
        if not isinstance(action, Action) :
            logging.error("%s.%s haven't return an Action, ignoring" % (self.__class__.__name__, f.__name__))
            return old_action
        return action
    aPreProcess.table[f.func_name] = {'function' : wrapper,
                                      'valid' : False,
                                      'reason' : 'Not Treated',
                                      'mandatory' : [],
                                      'optional' : {},
                                      'defaults' : {},
                                      'doc' : '',
                                      'original_func' : f
                                  }
    all_p = inspect.getargspec(f).args
    optional_value = inspect.getargspec(f).defaults
    #we don't want ot
    if not optional_value :
        aPreProcess.table[f.func_name]['mandatory'] = all_p
        aPreProcess.table[f.func_name]['optional'] = []
    else :
        nb_optional = len(optional_value)
        aPreProcess.table[f.func_name]['mandatory'] = all_p[:-nb_optional]
        aPreProcess.table[f.func_name]['optional'] = all_p[-nb_optional:]
        aPreProcess.table[f.func_name]['defaults'] = dict(zip(all_p[-nb_optional:], optional_value))
    if aPreProcess.table[f.func_name]['mandatory'] != ['self', 'action'] :
        logging.error('%s not allowed as preprocessing, bad signature'%(f.func_name))
        aPreProcess.table[f.func_name]['reason'] = "bad signature"
    else :
        aPreProcess.table[f.func_name]['valid'] = True
        aPreProcess.table[f.func_name]['reason'] = ""
        logging.debug("add %s to preprocess"%aPreProcess.table[f.func_name])
    return wrapper

aPreProcess.table = {}



#preprocessing decorator
def aPostProcess(f) :
    def wrapper(self, action) :
        old_action = action
        #pass it by copy
        action = f(self, copy.copy(action))
        if not isinstance(action, Action) :
            logging.error("%s.%s haven't return an Action, ignoring" % (self.__class__.__name__, f.__name__))
            return old_action
        return action
    aPostProcess.table[f.func_name] = {'function' : wrapper,
                                      'valid' : False,
                                      'reason' : 'Not Treated',
                                      'mandatory' : [],
                                      'optional' : {},
                                      'defaults' : {},
                                      'doc' : '',
                                      'original_func' : f
                                  }
    all_p = inspect.getargspec(f).args
    optional_value = inspect.getargspec(f).defaults
    #we don't want ot
    if not optional_value :
        aPostProcess.table[f.func_name]['mandatory'] = all_p
        aPostProcess.table[f.func_name]['optional'] = []
    else :
        nb_optional = len(optional_value)
        aPostProcess.table[f.func_name]['mandatory'] = all_p[:-nb_optional]
        aPostProcess.table[f.func_name]['optional'] = all_p[-nb_optional:]
        aPostProcess.table[f.func_name]['defaults'] = dict(zip(all_p[-nb_optional:], optional_value))
    if aPostProcess.table[f.func_name]['mandatory'] != ['self', 'action'] :
        logging.error('%s not allowed as preprocessing, bad signature'%(f.func_name))
        aPostProcess.table[f.func_name]['reason'] = "bad signature"
    else :
        aPostProcess.table[f.func_name]['valid'] = True
        aPostProcess.table[f.func_name]['reason'] = ""
        logging.debug("add %s to postprocess"%aPostProcess.table[f.func_name])
    return wrapper



aPostProcess.table = {}

class Executor():

    dependances = { "configuration" : [] ,
                    "interface" : [],
                    "transmission" : [],
                    "feature" : []}

    memory = []
    return_codes = {}

    def get_features(self):
        return self.feature__table

    def get_preprocess(self):
        return self.preprocess__table

    def get_postprocess(self):
        return self.postprocess__table


    def test(self) :
        print "test"

    def shutdown(self):
        pass



#class decorator

def anExecutor(cls):
    logging.debug("surcharging", cls, cls.__bases__)
    if cls.__bases__ :
        cls.__bases__ = (Executor,) + cls.__bases__
    else :
        cls.__bases__ = (Executor,)

    #list all methods known by the class
    known_methods = [getattr(cls, method).im_func for method in dir(cls) if inspect.ismethod(getattr(cls, method))]

    # we check methods in features table are really cls methods
    # by cleanning all function tables
    for table in [aFeature.table, aPreProcess.table, aPostProcess.table] :
        for method in table.keys() :
            if table[method]['function'] not in known_methods :
                logging.error("method %s not declared in %s (problem in declaration or missing decorator ?)" %
                              (method, cls.__name__))
                table.pop(method, None)
    # write the feature table 
    cls.feature__table = aFeature.table.copy()
    aFeature.table = {}

    cls.preprocess__table = aPreProcess.table.copy()
    aPreProcess.table = {}

    cls.postprocess__table = aPostProcess.table.copy()
    aPostProcess.table = {}

    return cls
