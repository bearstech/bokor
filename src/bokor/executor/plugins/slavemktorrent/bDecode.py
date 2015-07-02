#!/usr/bin/python
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

@file feature/__init__.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief bEncoding parser, encoder and decoder
"""
import re, sys
import os.path
from types import StringType, IntType, LongType, DictType, ListType, TupleType


#Tockent definition
ERR = 'err'
LIST_B = 'liste begin'
LIST_E = 'liste end'
DIC_B = 'dic begin'
DIC_E = 'dic end'
INT = 'int'
STR = 'str'


def getInt(text) :
    """Parse an integer

    @type  text: str
    @param text: Text to parse

    @return: Lenght parsed, integer parsed
    """
    sign = 1
    delta = text.find("e")
    integer = text[1:delta]
    if integer and integer[0] == "-" :
        integer = integer[1:]
        sign = -1
    if not integer.isdigit() :
        return (0, "'%s' is not a valid number"%integer)
    integer = int(integer)
    if integer == 0 and sign == -1 : return (0, "saddly -0 is not allow in bencode")
    return delta + 1, integer * sign

def getStr(text) :
    """Parse a string

    @type  text: str
    @param text: Text to parse

    @return: Lenght parsed, string parsed
    """
    sep = text.find(":")
    length_s = text[0:sep]

    if not length_s.isdigit() :
        return (0, "%s is not a valid size for a string"%text[0:sep])
    length = int(length_s)
    delta = len(length_s) + 1 + length
    return delta, text[sep + 1:sep+length + 1]


def lex(text) :
    """bEncoding lexer

    @type  text: str
    @param text: Text to parse

    @return: List of tokens
    """
    index = 0
    tokens = []
    awaited = []
    error = ""
    while index < len(text) :
        token = None
        value = None
        indexdelta = 0
        if text[index] == 'i' :
            token = INT
            indexdelta, value = getInt(text[index:])
            if indexdelta == 0 :
                token = ERR
                error = value
        elif text[index] == 'l' :
            token = LIST_B
            awaited = [(LIST_E, index)] + awaited
            indexdelta = 1
        elif text[index] == 'd' :
            token = DIC_B
            awaited = [(DIC_E, index)] + awaited
            indexdelta = 1
        elif text[index].isdigit() :
            token = STR
            indexdelta, value = getStr(text[index:])
            if indexdelta == 0 :
                token = ERR
                error = value
        elif text[index] == 'e' :
            if not awaited :
                token = ERR
            else :
                token = awaited[0][0]
                awaited = awaited[1:]
                indexdelta = 1
        else :
            token = ERR
        tokens.append((token, value))
        if token == ERR :
            if error :
                raise SyntaxError("syntax error, %s,  on index %s : %s.\n lexing state : %s. \n"%(error, index, text[index:], tokens))
            else :
                raise SyntaxError("syntax error on index %s : %s.\n lexing state : %s. \n"%(index, text[index:], tokens))
        index += indexdelta
    if awaited :
        token = awaited[0][0]
        index = awaited[0][1]
        msg = ""
        if token == LIST_E : msg = "The list open at %s is not closed"%index
        if token == LIST_E : msg = "The dictionary open at %s is not closed"%index
        raise SyntaxError("syntax error, structure not ending : awaiting : %s (%s)\n lexing state : %s. \n"%(token, msg, tokens))
    return tokens



def parseDict(tokens) :
    """Parse a dictionnary

    @type  tokens: list
    @param tokens: Lexed values

    @return: Parsed dictionnary
    """
    res = parse(tokens, DIC_E)
    if not res : return {}
    keys = res[0::2]
    values = res[1::2]
    if len(keys) > len(values) :
        raise SyntaxError("syntax error, in dict key '%s' has no value (content of dict so far : %s"%(keys[0], dict(zip(res[0::2][:-1], res[1::2]))))
    return  dict(zip(res[0::2], res[1::2]))

def parseList(tokens) :
    res = parse(tokens, LIST_E)
    return res


def parse(tokens, stop = None) :
    """bEncoding parser

    @type  tokens: list
    @param tokens: Lexed values

    @type  stop: object
    @param stop: Last element to parse

    @return: Parsed value as a list
    """
    res = []
    token = ERR
    value = None
    while tokens :
        token, value = tokens.pop(0)
        if token == stop: break
        if token == DIC_B :
            res.append(parseDict(tokens))
        elif token == LIST_B :
            res.append(parseList(tokens))
        elif token == INT or token == STR:
            res.append(value)
        else :
            raise SyntaxError("unknow token : %s", token)
    return res


def pusage(binname):
    """Print how this module should be used

    @type  binname: str
    @param binname: Path to the binary

    @return: Usage string
    """
    s = """use :
          %s bencoded string with space if you want
          or
          cmd | %s """%(binname, binname)
    print s


def decode(ben) :
    """Launch parser

    @type  ben: str
    @param ben: binary to parse

    @return: Parser result
    """
    return parse(lex(ben))







def encode_bencached(x,r):
    """Never called ???

    @type  x: str
    @param x: Element to encode

    @type  r: list
    @param r: Beginning of the encoded file

    @return:
    """
    r.append(x.bencoded)

def encode_int(x, r):
    """Integer encoder

    @type  x: str
    @param x: Element to encode

    @type  r: list
    @param r: Beginning of the encoded file

    @return: New encoded file as a list
    """
    r.extend(('i', str(x), 'e'))

def encode_bool(x, r):
    """Boolean encoder

    @type  x: str
    @param x: Element to encode

    @type  r: list
    @param r: Beginning of the encoded file

    @return: New encoded file as a list
    """
    if x:
        encode_int(1, r)
    else:
        encode_int(0, r)

def encode_string(x, r):
    """String encoder

    @type  x: str
    @param x: Element to encode

    @type  r: list
    @param r: Beginning of the encoded file

    @return: New encoded file as a list
    """
    r.extend((str(len(x)), ':', x))

def encode_list(x, r):
    """List encoder

    @type  x: str
    @param x: Element to encode

    @type  r: list
    @param r: Beginning of the encoded file

    @return: New encoded file as a list
    """
    r.append('l')
    for i in x:
        encode_func[type(i)](i, r)
    r.append('e')

def encode_dict(x,r):
    """Dict encoder

    @type  x: str
    @param x: Element to encode

    @type  r: list
    @param r: Beginning of the encoded file

    @return: New encoded file as a list
    """
    r.append('d')
    ilist = x.items()
    ilist.sort()
    for k, v in ilist:
        r.extend((str(len(k)), ':', k))
        encode_func[type(v)](v, r)
    r.append('e')

encode_func = {}
#encode_func[Bencached] = encode_bencached
encode_func[IntType] = encode_int
encode_func[LongType] = encode_int
encode_func[StringType] = encode_string
encode_func[ListType] = encode_list
encode_func[TupleType] = encode_list
encode_func[DictType] = encode_dict

try:
    from types import BooleanType
    encode_func[BooleanType] = encode_bool
except ImportError:
    pass

def bencode(x):
    """Encoder

    @type  x: str
    @param x: String to encode

    @return: Encoded string (str)
    """
    r = []
    encode_func[type(x)](x, r)
    return ''.join(r)


if __name__ == "__main__" :
    if len(sys.argv) > 1 :
        ben = " ".join(sys.argv[1:]).strip().decode('latin1')
    else :
        if sys.stdin.isatty():
            pusage(os.path.basename(sys.argv[0]))
            exit(0)
        else :
            ben = sys.stdin.read().strip()
    print decode(ben)
