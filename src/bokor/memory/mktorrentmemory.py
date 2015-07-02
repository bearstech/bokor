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

@file memory/mastertorrentmemory.py
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief sqlite memory class for bokor mktorrent functions
"""



from bokor.memory.sqlitememory import SqliteMemory
import sqlite3

class MkTorrentMemory(SqliteMemory):

    valid_filters = ['id',
                     'iddl',
                     'info_hash',
                     'relative_path',
                     'file',
                     'link'
                     'tracker',
                     'tmp_torrent',
                     'torrent_file',
                     'ftp_url',
                     'begin',
                     'status',
                     'file_exist',
                     'file_access',
                     'mktorrent_start',
                     'send_start',
                     'end',
                     'error',
                 ]
    def __init__(self, db):
        self.db = db
        self.connection = None
        self._init_memory()



    def _init_memory(self) :
        self.start()
        self.connection.row_factory = sqlite3.Row
        #check or create uploads
        self.execute(("CREATE TABLE if not exists "
                      "assets("
                      "id INTEGER PRIMARY KEY, "
                      "iddl INTEGER, "
                      "info_hash TEXT, "
                      "relative_path TEXT, "
                      "file TEXT, "
                      "link TEXT, "
                      "tracker TEXT, "
                      "tmp_torrent TEXT, "
                      "torrent_file TEXT, "
                      "ftp_url TEXT,"
                      "size_torrent INTEGER, "
                      "begin INTEGER, "
                      "status TEXT, "
                      "file_exist INTEGER, "
                      "file_access INTEGER, "
                      "mktorrent_start INTEGER, "
                      "send_start INTEGER, "
                      "end INTEGER, "
                      "error TEXT)"))
        self.connection.commit()
        
        
    def create_asset(self, asset) :
        idasset = self.add_row_and_get_id('assets',
                                          (None,
                                           asset['iddl'],
                                           asset['info_hash'],
                                           asset['relative_path'],
                                           asset['file'],
                                           asset['link'],
                                           asset['tracker'],
                                           asset['tmp_torrent'],
                                           asset['torrent_file'],
                                           asset['ftp_url'],
                                           asset['size_torrent'],
                                           asset['begin'],
                                           asset['status'],
                                           asset['file_exist'],
                                           asset['file_access'],
                                           asset['mktorrent_start'],
                                           asset['send_start'],
                                           asset['end'],
                                           asset['error'], ))
        return idasset


    def get_assets(self, filters = None, value = None, compare = "=") :
        c = self.connection.cursor()
        if filters in self.valid_filters and \
           compare in ["=", "==", "!="] and \
           value :
            c.execute("SELECT * FROM assets where %s%s?"%(filters, compare), (value,))
        else :
            c.execute("SELECT * FROM assets")
        c.connection.commit()
        rows = c.fetchall()
        if not rows :
            return []
        assets = []
        for row in rows:
            assets_d = {}
            for key in row.keys():
                assets_d[key] = row[key]
            assets.append(assets_d)
        return assets

    def update_asset(self, asset):
        c = self.connection.cursor()
        c.execute(("UPDATE assets SET iddl = ?, info_hash = ?, "
                   "relative_path = ?, "
                   "file = ?, link = ?, tracker = ?, tmp_torrent = ?, torrent_file = ?, "
                   "ftp_url = ?, size_torrent = ?, begin = ?, status = ?, file_exist = ?, "
                   "file_access = ?, mktorrent_start = ?, send_start = ?, "
                   "end = ?, error = ? WHERE id = ?"),
                  ( asset['iddl'],
                    asset['info_hash'],
                    asset['relative_path'],
                    asset['file'],
                    asset['link'],
                    asset['tracker'],
                    asset['tmp_torrent'],
                    asset['torrent_file'],
                    asset['ftp_url'],
                    asset['size_torrent'],
                    asset['begin'],
                    asset['status'],
                    asset['file_exist'],
                    asset['file_access'],
                    asset['mktorrent_start'],
                    asset['send_start'],
                    asset['end'],
                    asset['error'],
                    asset['id']))
        c.connection.commit()




    def delete_assets(self, filters, value, compare = "="):
        if filters not in self.valid_filters : return
        c = self.connection.cursor()
        c.execute("DELETE FROM assets WHERE %s%s?"%(filters, compare), (value,))
        c.connection.commit()
