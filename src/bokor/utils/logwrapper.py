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

@file transmission/__init__.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief logging tools
"""
#using decorator to survey
import inspect
import logging



def getFunArgs(f) :
    """Get arguments names from a function

    @type  f: function
    @param f: function to inspect

    @return: list of arguments (str)
    """
    f_argspec = inspect.getargspec(f)
    f_args = f_argspec.args
    f_defaults = f_argspec.defaults
    if f_defaults :
        arg_default = zip(f_args[-len(f_defaults):],f_defaults)
        arg_no_default = f_args[:-len(f_defaults)]
        string_arg = ", ".join(arg_no_default) + ", " + ", ".join([ "%s = %s"%(key, value) for key, value in arg_default ])
    else :
        string_arg = ", ".join(f_args)
    return string_arg


def logFunCall(f, *args, **kwargs) :
    """Log a function call

    @type  f: function
    @param f: function called

    @return: Nothing
    """
    string_arg = getFunArgs(f)
    if kwargs and args:
        logging.debug("Calling %s(%s) with arguments %s and named arguments %s"%(f.func_name, string_arg, str(args), str(kwargs)))
    elif args :
        logging.debug("Calling %s(%s) with arguments %s"%(f.func_name, string_arg, str(args)))
    elif kwargs :
        logging.debug("Calling %s()%s) with named arguments %s"%(f.func_name, string_arg, str(kwargs)))
    else :
        logging.debug("Calling %s(%s)"%(f.func_name, string_arg))


def logCall(f) :
    """Decorator to log function call

    @type  f: function
    @param f: Function that will be logged, then called

    @return: Decorator
    """
    def wrappedfunction(*args, **kwargs) :
        logFunCall(f, *args, **kwargs)
        return f(*args, **kwargs)
    return wrappedfunction



#@logCall
#def toto(a, b, c=5) :
#    pass

#@logCall
#def t(a, b) :
#    pass



if __name__ == '__main__' :
    logging.basicConfig(format='%(levelname)s:%(message)s',level=logging.DEBUG)
    toto(3, 4)

    t(3,4)

    parm = {'a': 2, 'b' : 5}
    toto(**parm)
