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
@brief usefull functions
"""

import pycurl
import urllib
import os, errno

def getfile(url, fd) :
    """

    @type  url: str
    @param url: URL to get

    @type  fd: file
    @param fd: file to write to

    @return: Nothing
    """
    url = urllib.unquote(url)
    url = url.encode('utf-8')
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.WRITEDATA, fd)
    curl.setopt(curl.SSL_VERIFYPEER, 0)
    curl.perform()
    curl.close()
    fd.seek(0)
    return


def age_sort(files):
    if len(files) <= 1:
        return files
    tmp = []
    for f in files:
        tmp.append(([f['age']], f))
    tmp.sort()
    i = 0
    res = []
    for k in tmp:
        res.append(k[1])
        res[-1]['id'] = i
        i += 1
    return res

def size_sort(files):
    if len(files) <= 1:
        return files
    tmp = []
    for f in files:
        tmp.append((f['size'], f))
    tmp.sort()
    i = 0
    res = []
    for k in tmp:
        res.append(k[1])
        res[-1]['id'] = i
        i += 1
    return res


def getLock(path):
    """Create a lock file at /tmp/cinego_prepare.lock with the O_EXCL flag

    @return: none
    """
    try:
        lockfd = os.open(path, os.O_CREAT | os.O_EXCL)
        os.close(lockfd)
        return True
    except OSError:  # Already locked
        return False


def rmLock(path):
    """Release lock file at /tmp/cinego_prepare.lock

    @return: True if lock is released, False otherwise
    """
    try:
        os.remove(path)
        return True
    except OSError:
        return False





def lastLine(hugefile, n, bsize=1024) :
    if not hugefile or not os.path.isfile(hugefile) : return []
    # get newlines type, open in universal mode to find it
    with open(hugefile, 'rU') as hfile:
        if not hfile.readline():
            return  # empty, no point
        sep = hfile.newlines  # After reading a line, python gives us this
    assert isinstance(sep, str), 'multiple newline types found, aborting'

    
    # find a suitable seek position in binary mode
    with open(hugefile, 'rb') as hfile:
        hfile.seek(0, os.SEEK_END)
        linecount = 0
        pos = 0

        while linecount <= n + 1:
            # read at least n lines + 1 more; we need to skip a partial line later on
            try:
                hfile.seek(-bsize, os.SEEK_CUR)           # go backwards
                linecount += hfile.read(bsize).count(sep) # count newlines
                hfile.seek(-bsize, os.SEEK_CUR)           # go backwards
            except IOError, e:
                if e.errno == errno.EINVAL:
                    # Attempted to seek past the start, can't go further
                    bsize = hfile.tell()
                    hfile.seek(0, os.SEEK_SET)
                    linecount += hfile.read(bsize).count(sep)
                    if linecount < n : n = linecount
                    break
                raise  # Some other I/O exception, re-raise
            pos = hfile.tell()

    res = []
    # Re-open in text mode
    with open(hugefile, 'r') as hfile:
        hfile.seek(pos, os.SEEK_SET)  # our file position from above
        for line in hfile:
            # We've located n lines *or more*, so skip if needed
            if linecount > n:
                linecount -= 1
                continue
            res.append(line.decode('utf8', 'replace').encode('utf8', 'replace').strip())
            # The rest we yield
    return res   


def ended_files_sort(res, func_name):
    globals()[func_name](res)
