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
@brief sqlite memory class for bokor postdl treatment
"""



from bokor.memory.sqlitememory import SqliteMemory
import sqlite3
import time

class PostMemory(SqliteMemory):

    rp_valid_filters = ["id",
                        "info_hash",
                        "relative_path",
                        "src",
                        "status",
                    ]

    cp_valid_filters = ["id",
                      "idrp",
                      "protocol",
                      "begin",
                      "status",
                      "src_exist",
                      "dst_url",
                      "dst_exist",
                      "dst_access",
                      "dst_creation",
                      "send_start",
                      "end",
                      "error",]

    def __init__(self, db):
        self.db = db 
        self.connection = None
        self._init_memory()

    def _init_memory(self) :
        self.start()
        self.connection.row_factory = sqlite3.Row
        #check or create uploads

        self.execute(("CREATE TABLE if not exists "
                      "relative_path("
                      "id INTEGER PRIMARY KEY, "
                      "created INTEGER, "
                      "info_hash TEXT, "
                      "relative_path TEXT, "
                      "src TEXT, "
                      "status TEXT)"))

        self.execute(("CREATE TABLE if not exists "
                      "movement("
                      "id INTEGER PRIMARY KEY, "
                      "created INTEGER, "
                      "idrp INTEGER, "
                      "protocol TEXT, "
                      "begin INTEGER, "
                      "status TEXT, "
                      "src_exist INTEGER, "
                      "dst_url TEXT, "
                      "dst_exist TEXT, "
                      "dst_access TEXT, "
                      "dst_creation INTEGER, "
                      "send_start INTEGER, "
                      "end INTEGER, "
                      "error TEXT ,"
                      "FOREIGN KEY(idrp) REFERENCES relative_path(id))"))
        self.connection.commit()

    def create_relative_path(self, relative_path) :
        now =  int(time.time())
        idrp = self.add_row_and_get_id('relative_path',
                                       (None,
                                        now,
                                        relative_path['info_hash'],
                                        relative_path['relative_path'],
                                        relative_path['src'],
                                        relative_path['status'],))
        return idrp


    def create_movement(self, movement):
        now =  int(time.time())
        idcp =  self.add_row_and_get_id('movement',
                                       (None,
                                        now,
                                        movement['idrp'],
                                        movement['protocol'],
                                        movement['begin'],
                                        movement['status'],
                                        movement['src_exist'],
                                        movement['dst_url'],
                                        movement['dst_exist'],
                                        movement['dst_access'],
                                        movement['dst_creation'],
                                        movement['send_start'],
                                        movement['end'],
                                        movement['error'], ))
        return idcp



    def get_relative_path(self, filters = None, value = None, compare = "=", get_mv = True):
        c = self.connection.cursor()
        if filters in self.rp_valid_filters and \
           compare in ["=", "==", "!="] and \
           value :
            c.execute("SELECT * FROM relative_path where %s%s?"%(filters, compare), (value,))
        else :
            c.execute("SELECT * FROM relative_path")
        c.connection.commit()
        rows = c.fetchall()
        if not rows :
            return []
        rps = []
        for row in rows:
            rps_d = {}
            for key in row.keys():
                rps_d[key] = row[key]
            rps.append(rps_d)
        if not get_mv :
            return rps
        for rp in rps :
            rp['movements'] = self.get_movements("idrp", rp["id"])
        return rps



    def get_a_relative_path(self, info_hash, relative_path):
        c = self.connection.cursor()
        c.execute("SELECT * FROM relative_path where info_hash = ? AND relative_path = ?", (info_hash, relative_path))
        c.connection.commit()
        row = c.fetchone()
        if not row :
            return None
        rp = {}
        for key in row.keys():
            rp[key] = row[key]
        rp['movements'] = self.get_movements("idrp", rp["id"])
        return rp


    def get_movements(self, filters = None, value = None, compare = "="):
        c = self.connection.cursor()
        if filters in self.cp_valid_filters and \
           compare in ["=", "==", "!="] and \
           value :
            c.execute("SELECT * FROM movement where %s%s?"%(filters, compare), (value,))
        else :
            c.execute("SELECT * FROM movement")
        c.connection.commit()
        rows = c.fetchall()
        if not rows :
            return []
        movements = []
        for row in rows:
            movements_d = {}
            for key in row.keys():
                movements_d[key] = row[key]
            movements.append(movements_d)

        return movements


    def update_relative_path(self, relative_path, update_mvt = False):
        c = self.connection.cursor()
        c.execute(("UPDATE relative_path SET "
                      "info_hash = ? , "
                      "relative_path = ? , "
                      "src = ? , "
                      "status = ? "
                      "WHERE id = ?"),
                     ( relative_path["info_hash"],
                       relative_path["relative_path"],
                       relative_path["src"],
                       relative_path["status"],
                       relative_path["id"]
                   ))
        c.connection.commit()
        if not update_mvt :
            return
        for movement in relative_path['movements'] :
            self.update_movement(movement)





    def update_movement(self, movement):
        c = self.connection.cursor()
        c.execute(("UPDATE movement SET "
                      "idrp = ?, "
                      "protocol = ?, "
                      "begin = ?, "
                      "status = ?, "
                      "src_exist = ?, "
                      "dst_url = ?, "
                      "dst_exist = ?, "
                      "dst_access = ?, "
                      "dst_creation = ?, "
                      "send_start = ?, "
                      "end = ?, "
                      "error = ? "
                      "WHERE id = ?"),
                     (movement["idrp"],
                      movement["protocol"],
                      movement["begin"],
                      movement["status"],
                      movement["src_exist"],
                      movement["dst_url"],
                      movement["dst_exist"],
                      movement["dst_access"],
                      movement["dst_creation"],
                      movement["send_start"],
                      movement["end"],
                      movement["error"],
                      movement["id"],
                  ))
        c.connection.commit()



    def delete_movement(self, filters, value, compare = "="):
        if filters not in self.cp_valid_filters : return
        c = self.connection.cursor()
        c.execute("DELETE FROM movement WHERE %s%s?"%(filters, compare), (value,))
        c.connection.commit()


    def delete_relative_path(self, filters, value, compare = "="):
        rps = self.get_relative_path(filters, value, compare)
        if filters not in self.rp_valid_filters : return
        c = self.connection.cursor()
        c.execute("DELETE FROM relative_path WHERE %s%s?"%(filters, compare), (value,))
        c.connection.commit()
        for rp in rps :
                self.delete_movement('idrp', rp['id'])
