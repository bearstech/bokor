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
@date 2014
@brief class to deal with rtorrent configuration
"""

import logging
from bokor.configuration.configurable import Configurable




rtorrent_conf_tmpl_mand = """
log.open_file = "rtorrent.log", %(path_log)s/rtorrent.log
log.add_output = "tracker_debug", "rtorrent.log"
log.add_output = "torrent_warn", "rtorrent.log"
log.add_output = "connection_warn", "rtorrent.log"
min_peers_seed = 1
check_hash = no
schedule = low_diskspace,0,6000,close_low_diskspace=0
bind=%(bind)s
set_max_file_size = -1
scgi_port = %(scgi)s:%(scgi_port)s
dht=disable

directory=%(directory)s
session=%(session)s
schedule=watch_directory_2,2,2,"load_start=*.torrent_upload,d.stop"
schedule=watch_directory_3,2,2,"load_start=*.torrent_upload_direct"
schedule=watch_directory_4,2,2,"load_start=*.torrent_treated"



system.method.set_key=event.download.finished,notify_me,"execute=%(post_dl)s,\\"$cat=$d.get_hash=\\",\\"$d.get_name=\\",\\"$d.get_directory_base=\\",%(db)s"
Ci_speed_up=%(ci_up)s
Ci_speed_down=%(ci_down)s
Ci_token_pro=%(ci_token_pro)s
port_range=%(port_min)s-%(port_max)s
"""


def write_conf_rtorrent(path, db,
                        ci_up, ci_down, token,
                        bind, port_min, port_max,
                        scgi_ip, scgi_port,
                        path_session, path_dl, path_log, post_dl,
                        down_kbps = None, up_kbps = None,
                        max_seed = None, max_leech = None) :
    """ write_conf_rtorrent


    """

    conf = rtorrent_conf_tmpl_mand%{
        'ci_up' : str(ci_up),
        'ci_down' : str(ci_down),
        'ci_token_pro' : str(token),
        'bind': str(bind),
        'port_min' : str(port_min),
        'port_max' : str(port_max),
        'scgi': str(scgi_ip),
        'scgi_port' : str(scgi_port),
        'session': str(path_session),
        'directory': str(path_dl),
        'path_log' : str(path_log),
        'post_dl' : str(post_dl),
        'db' : str(db),
    }
    if down_kbps : conf += "download_rate = %s \n"%str(int(down_kbps)/8)
    if up_kbps : conf += "upload_rate = %s \n"%str(int(up_kbps)/8)
    if max_seed : conf += "max_peers_seed = %s \n"%str(max_seed)
    if max_leech : conf += "max_peers_seed = %s \n"%str(max_leech)
    with open(path, 'w') as rconf :
        rconf.write(conf)
    return conf



