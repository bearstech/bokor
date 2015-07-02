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

@file memory/sqlitememory.py
@author Maurice AUDIN <maudin@bearstech.com>
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief sqlite memory class for bokor
"""

import sqlite3


class SqliteMemory():
    def __init__(self, db):
        self.db = db
        self.connection = None

    def start(self):
        self.connection = sqlite3.connect(self.db, check_same_thread=False)

    def add(self, table, rows):
        c = self.connection.cursor()
        for values in rows:
            c.execute("INSERT INTO %s VALUES (%s)" % (table, ",".join(['?' for x in values])), values)
        c.connection.commit()


    def fetch(self, table):
        c = self.connection.cursor()
        rows = c.execute("SELECT * from %s" % table)
        print rows.fetchall()

    def execute(self, command):
        c = self.connection.cursor()
        c.execute(command)
        self.connection.commit()

    def stop(self):
        self.connection.close()

    def add_row_and_get_id(self, table, values):
        c = self.connection.cursor()
        c.execute("INSERT INTO %s VALUES (%s)" % (table, ",".join(['?' for x in values])), values)
        last = c.lastrowid
        c.connection.commit()

        return last

if __name__ == "__main__":
    s = SqliteMemory()
    s.start()
    s.execute("CREATE TABLE test_table (date text)")
    s.add("test_table", [("test_value",)])
    s.stop()

    s.start()
    s.fetch("test_table")
    s.stop()
