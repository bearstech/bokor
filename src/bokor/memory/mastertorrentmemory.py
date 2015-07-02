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
@brief sqlite memory class for bokor master torrent
"""



from bokor.memory.sqlitememory import SqliteMemory
import sqlite3

class MasterTorrentMemory(SqliteMemory):
    def __init__(self, db):
        self.db = db
        self.connection = None
        self._init_memory()



    def _init_memory(self) :
        self.start()
        self.connection.row_factory = sqlite3.Row
        #check or create uploads 
        self.execute(("CREATE TABLE if not exists "
                      "uploads(iddl INTEGER PRIMARY KEY, "
                      "token TEXT, "
                      "token_file TEXT, "
                      "path_file TEXT, "
                      "tracker_url TEXT, "
                      "nb_files INTEGER, "
                      "nb_files_done INTEGER, "
                      "status TEXT)"))

        #check or create 
        self.execute(("CREATE TABLE if not exists "
                     "assets("
                     "id INTEGER PRIMARY KEY, "
                     "iddl INTEGER, "
                     "info_hash TEXT, "
                     "file_name TEXT, "
                     "size TEXT, "
                     "status TEXT, "
                     "url TEXT, "
                     "FOREIGN KEY(iddl) REFERENCES uploads(iddl))"))
        
        self.execute(("CREATE TABLE if not exists "
                     "relative_path("
                     "id_asset INTEGER, "
                     "path TEXT, "
                     "PRIMARY KEY (id_asset, path), "
                     "FOREIGN KEY(id_asset) REFERENCES assets(id))"))
        self.connection.commit()



    def get_uploads(self) :
        c = self.connection.cursor()
        c.execute("SELECT * FROM uploads")
        c.connection.commit()
        rows = c.fetchall()
        if not rows :
            return []
        res = []
        for row in rows :
            upload = { key : row[key] for key in row.keys()}
            iddl = upload['iddl']
            upload['assets'] = self.get_assets(iddl)

            res.append(upload)

        return res

    def add_row_and_get_id(self, table, values):
        c = self.connection.cursor()
        c.execute("INSERT INTO %s VALUES (%s)" % (table, ",".join(['?' for x in values])), values)
        last = c.lastrowid
        c.connection.commit()

        return last
        

    def create_upload(self, upload) :
        return self.add_row_and_get_id('uploads', (None, upload['token'], upload['token_file'], upload['path_file'], upload['tracker_url'], upload['nb_files'], upload['nb_files_done'], upload['status']))


    def create_asset(self, asset, iddl):
        return self.add_row_and_get_id('assets', (None, iddl, asset['info_hash'], asset['file_name'], asset['size'], asset['status'], asset['url']))


    def create_relative_path(self, rpath, idasset):
        return self.add('relative_path', [(idasset, rpath)])


    def update_upload(self, upload):
        c = self.connection.cursor()
        c.execute("UPDATE uploads SET token = ?, token_file = ?, path_file = ?, tracker_url = ?, nb_files = ?, nb_files_done = ?, status= ? where iddl = ?", (upload['token'], upload['token_file'], upload['path_file'], upload['tracker_url'], upload['nb_files'], upload['nb_files_done'], upload['status'], upload['iddl']))
        c.connection.commit()       
        
    def update_asset(self, asset, iddl):
        c = self.connection.cursor()
        c.execute("UPDATE assets SET iddl = ?, info_hash = ?, file_name = ?, size = ?, status = ?, url = ? where id = ?", (iddl, asset['info_hash'], asset['file_name'], asset['size'], asset['status'], asset['url'], asset['id'])) 
        c.connection.commit()       


    def create_relative_path_if_needed(self, rpathes, idasset) :
        known_rpath =self.get_relative_path(idasset)  
        for rpath in rpathes :
            if rpath in known_rpath :
                continue
            self.create_relative_path(rpath, idasset)



    def update_or_crate_asset(self, info_hash, asset, iddl) :
        asset['info_hash'] = info_hash
        if not asset['id'] :
            asset['id'] = self.create_asset(asset, iddl)
        else:
             self.update_asset(asset, iddl)
        
        
    def get_upload(self, iddl):
        c = self.connection.cursor()
	c.execute("SELECT * FROM uploads where iddl=?", (iddl,))
        c.connection.commit()
        row = c.fetchone()
        if not row :
            return {}
        upload = { key : row[key] for key in row.keys()}
        upload['assets'] = self.get_assets(iddl)
        return upload

    def get_assets(self, iddl):
        c = self.connection.cursor()
        c.execute("SELECT * FROM assets where iddl=?", (iddl,))
        c.connection.commit()
        rows = c.fetchall()
        if not rows :
            return {}
        assets = {row["info_hash"] : {'status' : row['status'],
                                      'info_hash': row['info_hash'],
                                      'file_name' : row['file_name'],
                                      'size' : row['size'],
                                      'url' : row['url'],
                                      'id' : row['id'],
                                      'relative_path' : self.get_relative_path(row['id']) } for row in rows}
        return assets

    def get_relative_path(self, idasset):
        c = self.connection.cursor()
        c.execute("SELECT * FROM relative_path where id_asset=?", (idasset, ))
        c.connection.commit()
        rows = c.fetchall()
        if not rows :
            return []
        relative_path = [row["path"] for row in rows]
        return relative_path


    
        
