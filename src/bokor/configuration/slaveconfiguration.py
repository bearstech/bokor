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

@file 
@author Olivier ANDRE <zitune@bearstech.com>
@date 2014
@brief configuration class dedicated to slave
"""


from bokor.configuration.baseconfiguration import BaseConfiguration
from bokor.executor.executor import Executor, aFeature, anExecutor, aPreProcess
import glob
import logging

from os import rename, remove
from os.path import isfile, realpath, dirname, expanduser, exists
from time import time


class SlaveConfiguration(BaseConfiguration):


    def load_conf_file(self):
        BaseConfiguration.load_conf_file(self)
        self.treatTms()



    def getTmsConf(self, tms) :
        """retrieve tms config in a dict
        
        @type  tms: string
        @param tms: path of the tmc
        
        @return: dict of tms conf or None
        """
        tmsrc = open(tms, 'r')
        try :
            defaults = dict(map((lambda (x, y) : (x.strip(), y.strip())), [line.split("=")  for line in tmsrc if line != '\n']))
        except :
            return None
        finally:
            tmsrc.close()
        return defaults

    def archiveTms(self, tms_file) :
        """archive the tms_file (max(nb_arch, 3) are concerveted )
        
        @type  tms_file: str
        @param tms_file: path to the tms config file
        
        @return: return path of the archive
        """
        nb_arch = 15
        archives = glob.glob(tms_file+'_*')
        archives.sort(reverse=True)
        nb_arch = max(nb_arch, 3)
        if len(archives) >= nb_arch :
            for f in archives[(nb_arch - 1):] :
                remove(f)
        arch_path = tms_file + "_" + str(time())
        rename(tms_file, arch_path)
        return arch_path



    def treatTms(self):
        """try to include tms config file into cinego config file
        
        @type  config: str
        @param config: path to the cinego config file
        
        @return: none
        """
        tms_file = realpath(expanduser(dirname(self.conf_file) + '/tms.rc'))
        if not exists(tms_file) :
            return
        tms_conf = self.getTmsConf(tms_file)
        if not tms_conf :
            arch_path = self.archiveTms(tms_file)
            logging.error("could not read valid conf from (skipping TMS conf) : %s "%(arch_path))
            return
        try :
            new_config = self.writeTms(tms_conf)
        except Exception as error:
            arch_path = self.archiveTms(tms_file)
            logging.error("could not write conf (%s) from  : %s : %s"%(error, arch_path, str(tms_conf)))
            return
        arch_path = self.archiveTms(tms_file)
        logging.info("update conf from  : %s : %s"%(arch_path, str(tms_conf)))
        return
    


        
    def writeTms(self, tms_conf) :
        """archive the tms_file (max(nb_arch, 3) are concerveted )
        
        @type  config: str
        @param config: path to the cinego config file
        
        @type  tms_conf: str
        @param tms_conf: path to the tms config file
        
        @return: return path of the archive
        """
        login = ''
        password = ''
        host = '127.0.0.1'
        root = '/'
    
    
        if not self._config.has_section("TMS") :
            self._config.add_section("TMS")
        for key, value in tms_conf.iteritems() :
            if key == 'Token' :
                self._config.set("bokor", 'token', value)
            self._config.set("TMS", key, value)
            
        if tms_conf.has_key('LibIp'):
            host = tms_conf['LibIp']
        if tms_conf.has_key('LibLogin'):
            login = tms_conf['LibLogin']
        if tms_conf.has_key('LibPass'):
            password = tms_conf['LibPass']
        if tms_conf.has_key('LibFolder'):
            root = tms_conf['LibFolder']

            
        if tms_conf.has_key('TmsBuffer'):
            self._config.set("rtorrent", "path_dl", tms_conf['TmsBuffer'])

        self._config.set("post", "protocol", 'ftp')
        self._config.set("post", "base_url", 'ftp://%s:%s@%s/%s'%(login, password, host, root))
        
            
        self.write_conf()
        return 
