# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php

import mysql.connector
from server_common.utilities import print_and_log

class SQLAbstraction(object):
    """A wrapper to connect to MySQL databases"""

    # Number of available simultaneous connections to each connection pool
    POOL_SIZE = 16

    def __init__(self, dbid, user, password, host="127.0.0.1"):
        """Constructor

        Args:
            dbid (string): The id of the database that holds the required information
            user (string): The username to use to connect to the database
            password (string): The password to use to connect to the database
            host (string): The host address to use, defaults to local host
        """
        self._dbid = dbid
        self._user = user
        self._password = password
        self._host = host
        self._pool_name = self._generate_pool_name()
        self._start_connection_pool()

    @staticmethod
    def generate_unique_pool_name():
        """Generate a unique name for the connection pool so each object has its own pool
        """
        import uuid
        return "DBSVR_CONNECTION_POOL_" + str(uuid.uuid4())

    def _generate_pool_name(self):
        """Generate a name for the connection pool based on host, user and database name
           a connection in the pool is made with the frist set of credentials passed, so we
           have to make sure a pool name is not used with different credentials
        """
        return "DBSVR_%s_%s_%s" % (self._host, self._dbid, self._user)

    def _start_connection_pool(self):
        """Initialises a connection pool
        """
        print_and_log("Creating a new connection pool: " + self._pool_name)
        conn = mysql.connector.connect(user=self._user, password=self._password, host=self._host, database=self._dbid,
                                       pool_name=self._pool_name,
                                       pool_size=SQLAbstraction.POOL_SIZE)
        curs = conn.cursor()
        # Check db exists
        curs.execute("SHOW TABLES")
        if len(curs.fetchall()) == 0:
            # Database does not exist
            raise Exception("Requested Database %s does not exist" % self._dbid)
        curs.close()
        conn.close()

    def _get_connection(self):
        try:
            return mysql.connector.connect(pool_name=self._pool_name)
        except Exception as err:
            raise Exception("Unable to get connection from pool: %s" % err.message)

    def execute_command(self, command, is_query):
        """Executes a command on the database, and returns all values

        Args:
            command (string): the SQL command to run
            is_query (boolean): is this a query (i.e. do we expect return values)

        Returns:
            values (list): list of all rows returned. None if not is_query
        """
        conn = None
        curs = None
        values = None
        try:
            conn = self._get_connection()
            curs = conn.cursor()
            curs.execute(command)
            if is_query:
                values = curs.fetchall()
            # Commit as part of the query or results won't be updated between subsequent transactions. Can lead
            # to values not auto-updating in the GUI.
            conn.commit()
        except Exception as err:
            print_and_log("Error executing command on database: %s" % err.message, "MAJOR")
        finally:
            if curs is not None:
                curs.close()
            if conn is not None:
                conn.close()
        return values

    def query(self, command):
        """Executes a query on the database, and returns all values

        Args:
            command (string): the SQL command to run

        Returns:
            values (list): list of all rows returned
        """
        return SQLAbstraction.execute_command(self, command, True)

    def update(self, command):
        """Executes an update on the database, and returns all values

        Args:
            command (string): the SQL command to run
        """
        SQLAbstraction.execute_command(self, command, False)
