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
@brief Retrieve hash from a torrent file
"""
import sys, os, hashlib, StringIO, bDecode



def getHashFromFd(torrent_file) :
    """Get hash from a torrent file descriptor

    @type  torrent_file: file
    @param torrent_file: torrent file to hash

    @return: Torrent hash
    """
    res = torrent_file.read()
    metainfo = bDecode.decode(res)[0]

    info = metainfo['info']
    pieces = StringIO.StringIO(info['pieces'])
    torrent_file.seek(0)
    return hashlib.sha1(bDecode.bencode(info)).hexdigest().upper()



def getSizeFromFd(torrent_file) :
    """Get hash from a torrent file descriptor

    @type  torrent_file: fd
    @param torrent_file: torrent file 

    @return: size
    """
    res = torrent_file.read()
    metainfo = bDecode.decode(res)[0]

    info = metainfo['info']
    torrent_file.seek(0)
    return int(info['length'])



def getSize(path) :
    """Get hash from a torrent file

    @type  path: string
    @param path: torrent file 

    @return: size
    """
    with open(path, "rb") as torrent_file  :
        res = getSizeFromFd(torrent_file)
    return res


def getHash(path):
    """Get hash from a torrent file path

    @type  path: str
    @param path: path to the torrent file

    @return: Torrent hash
    """
    # Open torrent file
    with open(path, "rb") as torrent_file  :
        res = getHashFromFd(torrent_file)
    return res



if __name__ == "__main__":
    print getHash(sys.argv[1])
