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
@brief process orders for bokor master for rtorrent management
"""

import logging
import os
from bokor.executor.executor import Executor
from bokor.constants.error import *
from bokor.executor.master import Master
from bokor.executor.executor import  aFeature, anExecutor, aPreProcess, aPostProcess
from bokor.configuration.configurable import Configurable
from bokor.transmission.unsafesocket import UnsafeSocket
from bokor.memory.mastertorrentmemory import MasterTorrentMemory
from bokor.utils.hashtorrent import  getHash


@anExecutor
class MasterTorrent(Master):


    dependances = { "configuration" : [] ,
                    "interface" : [],
                    "transmission" : [UnsafeSocket],
                    "feature" : []}

    needed_configuration = {"upload":
                            {
                                "path_ftp": {'mandatory' : True, 'type' : 'file' , 'permission' : 'drx', 'exist' : True},
                                "path_repo": {'mandatory' : True, 'type' : 'file' , 'permission' : 'drwx', 'exist' : True},
                                "url_repo": {'mandatory' : True, 'type' : 'string'},
                            },
                            "memory" :
                            {
                                "sqlitedir": {'mandatory' : False, 'type' : 'file' , 'permission' : 'drwx', 'exist' : True}, 
                            },
                        }

    def __init__(self, bokor):
        self.bokor = bokor
        self.db = self.get('memory', 'sqlitedir', '/tmp')  + '/' + 'master.db'
        self.memory = MasterTorrentMemory(self.db)
        self.path_ftp = self.bokor.get("upload", "path_ftp")
        if self.path_ftp[-1:] != '/' : self.path_ftp += '/'
        self.path_repo = self.bokor.get("upload", "path_repo")
        if self.path_repo[-1:] != '/' : self.path_repo += '/'
        self.url_repo = self.bokor.get("upload", "url_repo")
        if self.url_repo[-1:] != '/' : self.url_repo += '/'
        self.check()



    def _save_upload(self, upload):
        self.memory.update_upload(upload)
        for asset in upload['assets'] :
            self.memory.update_or_crate_asset(asset, upload['assets'][asset], upload['iddl'])
            self.memory.create_relative_path_if_needed(upload['assets'][asset]['relative_path'], upload['assets'][asset]['id'])

    
#------------------------------------------------------------------------------
# add_file management

    @aPreProcess
    def pre_add_file(self, action):
        #add file is not to be tried on a master
        action.execute = False

        peers = self.bokor.transmission.get_peers(action)
        if action.ressources and not peers :
            #peer not connected letting transmission deal with this
            action.post = False
            return action
        if not peers or len(peers) > 1 :
            action.transmit = False
            action.results = "add_file requier a peer token"
            action.code = PEER_MANDATORY 
            return action
        peer = peers[0]
        token_file = ''
        if 'token_file' in action.params :
            token_file = action.params['token_file']
        path_file = ''
        if 'path_file' in action.params :
            path_file = action.params['path_file']
        tracker_url = ''
        if 'tracker_url' in action.params :
            tracker_url = action.params['tracker_url']
        upload = {'token': peer.token,
                  'nb_files': -1,
                  'nb_files_done': 0,
                  'token_file' : token_file,
                  'path_file' : path_file,
                  'tracker_url' : tracker_url,
                  'status' : 'new'
              }
        iddl = str(self.memory.create_upload(upload))
        action.params['iddl'] = iddl
        return action


    @aPostProcess
    def post_add_file(self, action):
        #if no iddl exit
        if not action.params['iddl'] :
            return action
        iddl = action.params['iddl']
        #if no valid reponse from a peer
        if not action.transmitted_answer or "code" not in action.transmitted_answer[0] :
            return action
        # if the add file take place but something went wrong
        # we update
        upload = self.memory.get_upload(iddl)
        if action.transmitted_answer[0]["code"] != SUCCESS:
            upload['status'] = 'error'
        
        upload['nb_files'] = len(action.transmitted_answer[0]["answer"])
        self.memory.update_upload(upload)
        
        action.transmitted_answer[0]["answer"] = iddl
        return action


#------------------------------------------------------------------------------
# notify_upload and management

    @aPreProcess
    def pre_notify_upload(self, action):
        return self._execute_and_block_transmit(action)

    @aFeature
    def notify_upload(self, seeder, infohash,
                      iddl, relative_path, file_name, status, size):
        """
        allow a peer to notfify the end of a file preparation
        """
        print (self, seeder, infohash,
                      iddl, relative_path, file_name, status, size)
        upload = self.memory.get_upload(iddl)
        if not upload :
            self._bokor_code = 99
            return "iddl is not valid"

        upload['status'] = "pending"

        
        upload['assets'] = self.memory.get_assets(iddl)
        
        if infohash not in upload['assets']:
            upload['assets'][infohash] = {'id' : None}
        upload['assets'][infohash]['status'] = status
        upload['assets'][infohash]['size'] = size
        upload['assets'][infohash]['file_name'] = file_name
        if 'relative_path' in upload['assets'][infohash]:
            upload['assets'][infohash][
                'relative_path'].append(relative_path)
        else:
            upload['assets'][infohash][
                'relative_path'] = [relative_path]

        upload['assets'][infohash][
            'url'] = self.url_repo + infohash + ".torrent"

        # how many file do we know ? we must count the relative pathes, not the
        # infohasheshes
        nb_known = 0
        for h_file in upload['assets']:
            nb_known += len(
                upload['assets'][h_file]['relative_path'])

        upload['nb_files_done'] = nb_known

        if upload['nb_files_done'] == \
           upload['nb_files']:
            gstatus = "done"
            for hashf in upload['assets']:
                if upload['assets'][hashf]['status'] == "error":
                    gstatus = "error"
                    break
                if (gstatus in ['done', 'unvalidated', 'known']) and upload['assets'][hashf]['status'] == "unvalidated":
                    gstatus = "unvalidated"
                if (gstatus in ['done', 'known']) and upload['assets'][hashf]['status'] == "known":
                    gstatus = "known"
                    
            upload['status'] = gstatus
            pass  # fix me call cinego

        self._save_upload(upload)
        if self._prepareFile(infohash):
            pass
            #sendMail("seeder: " + str(seeder) + "\ninfoash: " + str(infohash) +
            #         "\niddl: " + str(iddl) + "\nstatus: " + str(status))
        return upload

    def _prepareFile(self, infohash):
        # prepare file to be ready for acces to other peers
        # fixme: most of this should be in config file
        import shutil
        if os.path.isfile(self.path_repo + infohash + ".torrent") :
            logging.info(
                "%s.torrent already exists in %s , should not happen" %
                (infohash, self.path_repo))
            return False  # not a new dl
        else:
            logging.info("shutil.move('" + self.path_ftp + infohash +
                         ".torrent', '" + self.path_repo + infohash + ".torrent'")
            shutil.move(self.path_ftp + infohash +
                         ".torrent",  self.path_repo + infohash + ".torrent")
            if getHash(self.path_repo + infohash + ".torrent") != infohash:
                logiging.error("infohash mismatch, upload has failed")
                # fixme: remove .torrent ? handle error
        return True


#------------------------------------------------------------------------------
# list_upload and management

    @aPreProcess
    def pre_list_uploads(self, action) :
        return self._execute_and_block_transmit(action)



    @aFeature
    def list_uploads(self, iddl = None):
        if iddl :
            uploads = self.memory.get_upload(iddl)
        else :
            uploads = self.memory.get_uploads()
        return uploads


#------------------------------------------------------------------------------
# validate and management
    
    @aPreProcess
    def pre_validate(self, action):
        if 'iddl' not in action.params.keys():
            return action
        iddl = unicode(action.params['iddl'])
        upload = self.memory.get_upload(iddl)
        if not upload :
            #we buid the results saying that the iddl is invalid
            action.results = "validate on an unknown iddl : %s"%iddl
            action.code = VALUE_UNFIT
            #we block all future answer
            action.execute = False
            action.transmit = False
            action.post = False
            return action

        hashfiles = upload['assets'].keys()
        if not hashfiles:
            raise RuntimeError("iddl %s is empty" % iddl)
        relpath = [{'hashfile': infohash,
                     'relative_path':  upload['assets'][infohash]['relative_path'][0]}
                    for infohash in upload['assets'].keys()]
        action.params['token_site'] = upload['token']
        action.params['hash_pathes'] = relpath
        action.ressources = [upload['token']]
        return action


    @aPostProcess
    def post_validate(self, action):
        if not action.transmitted_answer :
            return action
        if  action.transmitted_answer[0]['code'] != SUCCESS :
            return action
        res = action.transmitted_answer[0][u'answer']
        iddl = unicode(action.params['iddl'])
        upload = self.memory.get_upload(iddl)
        totstatus = True
        for hashf, state in res.items() :
            if state:
                upload['assets'][hashf]['status'] = "done"
            else:
                upload['assets'][hashf]['status'] = "error"
        hashes = upload['assets'].keys()

        for hashf in hashes:
            totstatus = totstatus and (
                upload['assets'][hashf]['status'] == "done")

        if totstatus and \
           upload['nb_files_done'] == \
           upload['nb_files']:
            upload['status'] = "done"

        action.code = SUCCESS
        action.results = totstatus
        action.transmitted_answer = []
        self._save_upload(upload)
        return action

#------------------------------------------------------------------------------
# PEER management




    @aFeature
    def list_peers(self, status) :
        """
        list_peers return all peers with a specific status

        """
        # FIXME RETRO
        return [{'token_site': peer.token,
                 'ip': peer.ip,
                 'port': peer.port,
                 'superseeder': int(peer.ci_up) == -1 if "ci_up" in peer.__dict__.keys() else False,
                 'misfit' : peer.misfit,
                 'version' : peer.version,
                 'category' : peer.category,
                 'status' : peer.status}
                for peer in self.bokor.transmission.peers if peer.status == status]        


    @aPreProcess
    def pre_showsuperseeders(self, action) :
        return self._execute_and_block_transmit(action)



    @aFeature
    def showsuperseeders(self):
        return [{'token_site': peer.token,
                 'ip': peer.ip,
                 'port': peer.port}
                for peer in self.bokor.transmission.peers if "ci_up" in peer.__dict__ and  int(peer.ci_up) == -1]



    @aPreProcess
    def pre_showpeer(self, action) :
        return self._execute_and_block_transmit(action)

    @aFeature
    def showpeer(self, token):
        for peer in self.bokor.transmission.peers :
            if peer.peername == token_site :
                return str(peer)
        


# post status_*





    @aPostProcess
    def post_status_view(self, action):
        if not action.transmitted_answer :
            return action
        peers = { x.ip : x.token for x in  self.bokor.transmission.peers }
        for peer_res in  action.transmitted_answer :
            if  peer_res['code'] != SUCCESS :
                continue
            res = peer_res["answer"]
            if not isinstance(res, list) :
                continue
            for dl in res :
                for peer in dl["peers"] :
                    if peer["ip"] in peers : 
                        peer["token"] = peers[peer["ip"]]
        return action


    @aPostProcess
    def status_exchange(self, action):
        return self.post_status_view(action)


    @aPostProcess
    def status_download(self, action):
        return self.post_status_view(action)


    @aPostProcess
    def status_upload(self, action):
        return self.post_status_view(action)


    @aPostProcess
    def status_paused(self, action):
        return self.post_status_view(action)

        

    @aPreProcess
    def pre_get_conf(self, action) :
        action.execute = True
        return action

    @aPreProcess
    def pre_get_conf(self, action):
        action.execute = True
        return action

    @aPreProcess
    def pre_set_conf(self, action):
        action.execute = True
        return action

    @aPreProcess
    def pre_write_conf(self, action):
        action.execute = True
        return action

    @aPreProcess
    def pre_create_section(self, action):
        action.execute = True
        return action

    @aPreProcess
    def pre_remove_option(self, action):
        action.execute = True
        return action

    @aPreProcess
    def pre_remove_section(self, action):
        action.execute = True
        return action



    
