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
@author Maurice AUDIN <maudin@bearstech.com>
@date 2014
@brief
"""
#!/usr/bin/python

import urllib
import httplib
import getopt
import sys
from time import time
import random
from threading import Thread, currentThread
from math import pow, sqrt
import bisect
import re

HOST = 'test.cinego-cgp2p.bearstech.com'
RUNS = 1
VERBOSE = 0
HTTPDEBUG = 0
DOWNLOAD_FILES = ['/1M', '/5M', '/10M']
UPLOAD_FILES = [132884, 493638]


def printv(msg):
    if VERBOSE:
        print msg


def downloadthread(connection, url):
    connection.request('GET', url, None, {'Connection': 'Keep-Alive'})
    response = connection.getresponse()
    self_thread = currentThread()
    self_thread.downloaded = len(response.read())


def download(exclude=[]):
    total_downloaded = 0
    connections = []
    for run in range(RUNS):
        connection = httplib.HTTPConnection(HOST)
        connection.set_debuglevel(HTTPDEBUG)
        connection.connect()
        connections.append(connection)
    total_start_time = time()
    for current_file in [x for x in DOWNLOAD_FILES if x not in exclude]:
        threads = []
        for run in range(RUNS):
            thread = Thread(target=downloadthread,
                            args=(connections[run], current_file))
            thread.run_number = run
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
            total_downloaded += thread.downloaded
            printv('Run %d for %s finished' %
                   (thread.run_number, current_file))
    total_ms = (time() - total_start_time) * 1000
    for connection in connections:
        connection.close()
    printv('Took %d ms to download %d bytes' % (total_ms, total_downloaded))
    return (total_downloaded * 8000 / total_ms)


def uploadthread(connection, data):
    url = '/upload.php'
    connection.request('POST', url, data,
                       {'Connection': 'Keep-Alive',
                        'Content-Type': 'application/x-www-form-urlencoded'})
    response = connection.getresponse()
    reply = response.read()
    self_thread = currentThread()
    self_thread.uploaded = int(reply.split('=')[1])


def upload():
    connections = []
    for run in range(RUNS):
        connection = httplib.HTTPConnection(HOST)
        connection.set_debuglevel(HTTPDEBUG)
        connection.connect()
        connections.append(connection)

    post_data = []
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for current_file_size in UPLOAD_FILES:
        values = {'content': ''.join(random.choice(ALPHABET)
                                     for i in range(current_file_size))}
        post_data.append(urllib.urlencode(values))

    total_uploaded = 0
    total_start_time = time()
    for data in post_data:
        threads = []
        for run in range(RUNS):
            thread = Thread(target=uploadthread, args=(connections[run], data))
            thread.run_number = run
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
            printv('Run %d for %d bytes finished' %
                   (thread.run_number, thread.uploaded))
            total_uploaded += thread.uploaded
    total_ms = (time() - total_start_time) * 1000
    for connection in connections:
        connection.close()
    printv('Took %d ms to upload %d bytes' % (total_ms, total_uploaded))
    return (total_uploaded * 8000 / total_ms)


def ping():
    connection = httplib.HTTPConnection(HOST)
    connection.set_debuglevel(HTTPDEBUG)
    connection.connect()
    times = []
    worst = 0
    for i in range(5):
        total_start_time = time()
        connection.request('GET', '/0M', None, {'Connection': 'Keep-Alive'})
        response = connection.getresponse()
        response.read()
        total_ms = time() - total_start_time
        times.append(total_ms)
        if total_ms > worst:
            worst = total_ms
    times.remove(worst)
    total_ms = sum(times) * 250  # * 1000 / number of tries (4) = 250
    connection.close()
    printv('Latency for %s - %d' % (HOST, total_ms))
    return total_ms


def usage():
    print '''
usage: bwtest.py [-h] [-v] [-r N] [-m M] [-d L]

Test your bandwidth speed to your own server.

optional arguments:
 -h, --help         show this help message and exit
 -v                 enabled verbose mode
 -r N, --runs=N     use N runs (default is 1).
 -m M, --mode=M     test mode: 1 - download, 2 - upload, 4 - ping,
    1 + 2 + 4 = 7 - all (default).
 -d L, --debug=L    set httpconnection debug level (default is 0).
'''


def main():
    global VERBOSE, RUNS, HTTPDEBUG, HOST
    mode = 7
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hr:vm:d:s",
                                   ["help", "runs=", "mode=", "debug="])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)
    for o, a in opts:
        if o == "-v":
            VERBOSE = 1
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-r", "--runs"):
            try:
                RUNS = int(a)
            except ValueError:
                print 'Bad runs value'
                sys.exit(2)
        elif o in ("-m", "--mode"):
            try:
                mode = int(a)
            except ValueError:
                print 'Bad mode value'
                sys.exit(2)
        elif o in ("-d", "--debug"):
            try:
                HTTPDEBUG = int(a)
            except ValueError:
                print 'Bad debug value'
                sys.exit(2)

    if mode & 4 == 4:
        print 'Ping: %d ms' % ping()
    if mode & 1 == 1:
        print 'Download speed: ' + pretty_speed(download())
    if mode & 2 == 2:
        print 'Upload speed: ' + pretty_speed(upload())


def pretty_speed(speed):
    units = ['bps', 'Kbps', 'Mbps', 'Gbps']
    unit = 0
    while speed >= 1024:
        speed /= 1024
        unit += 1
    return '%0.2f %s' % (speed, units[unit])

if __name__ == '__main__':
    main()
