# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DbConnections

 Manage QGIS connections to QGISCloud databases
                             -------------------
        begin                : 2011-09-21
        copyright            : (C) 2011 by Sourcepole
        email                : pka@sourcepole.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from db_connection_cfg import DbConnectionCfg
import time
import socket

class DbConnections:

    def __init__(self):
        self._dbs = {} # Map<dbname, DbConnectionCfg>
        self._dbs_refreshed = False

    def add_from_json(self, db):
        self._dbs[db['name']] = DbConnectionCfg(db['host'], db['port'], db['name'], db['username'], db['password'])

    def count(self):
        return len(self._dbs)

    def iteritems(self):
        return self._dbs.iteritems()

    def db(self, dbname):
        return self._dbs[unicode(dbname)]

    def refreshed(self):
        return self._dbs_refreshed

    def refresh(self, user):
        cloud_connections_key = u"/qgiscloud/connections/%s" % user
        settings = QSettings()

        cloud_dbs_from_server = self._dbs.keys()
        stored_connections = settings.value(cloud_connections_key) or []
        cloud_dbs_from_settings = map(lambda conn: str(conn), pystringlist(stored_connections))

        # remove obsolete connections
        for db_name in (set(cloud_dbs_from_settings) - set(cloud_dbs_from_server)):
            for connection in DbConnectionCfg.get_cloud_db_connections(db_name):
                DbConnectionCfg.remove_connection(connection)

        # add missing connections
        for db_name in cloud_dbs_from_server:
            if len(DbConnectionCfg.get_cloud_db_connections(db_name)) == 0:
                self.db(db_name).store_connection()

        # store cloud db names in settings
        if len(cloud_dbs_from_server) > 0:
            settings.setValue(cloud_connections_key, cloud_dbs_from_server)
        else:
            settings.remove(cloud_connections_key)

        self._dbs_refreshed = True

    def cloud_layer_uri(self, db_name, table_name, geom_column):
        uri = None
        # find db connection and create uri
        connections = DbConnectionCfg.get_cloud_db_connections(db_name)
        if len(connections) > 0:
            conn = DbConnectionCfg.from_settings(connections[0])
            uri = conn.data_source_uri()
            uri.setDataSource("", table_name, geom_column)
        return uri

    def isPortOpen(self, db_name):
        uri = self.cloud_layer_uri(db_name, "", "")
        if not uri.port():
            return False
        host = str(uri.host())
        port = int(uri.port())
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            s.shutdown(2)
            return True
        except:
            return False

    # Wait until cloud database is available (creation is asynchronous)
    @staticmethod
    def wait_for_db(db, timeout = 3, retries = 5, sleeptime = 3):
        ok = False
        while not ok and retries > 0:
            try:
                connection = db.dbapi_connection(timeout)
                connection.close()
                ok = True
            except Exception: # as err:
                retries -= 1
                if retries == 0:
                    raise
                else:
                    time.sleep(sleeptime)
