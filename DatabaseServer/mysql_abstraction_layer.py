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


class SQLAbstraction(object):
    """A wrapper to connect to MySQL databases"""

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
        self._conn = None
        self._curs = None

    def check_db_okay(self):
        """Attempts to connect to the database and raises an error if not able to do so
        """
        try:
            self.open_connection_if_closed()
            self.close_connection()
        except Exception as err:
            raise Exception(err)

    def open_connection_if_closed(self):
        if self._conn is None:
            try:
                self._conn, self._curs = self.__open_connection()
            except Exception as err:
                raise Exception(err)

    def reset_connection(self):
        try:
            self.close_connection()
            self.open_connection_if_closed()
        except Exception as err:
            raise Exception("Unable to reset database connection: %s" % err)

    def close_connection(self):
        if self._conn is not None:
            self._curs.close()
            self._conn.close()
        self._curs = None
        self._conn = None

    def __open_connection(self):
        """Open a connection to the database

        Returns:
            conn (mysql connector): a connection to the database
            curs (mysql cursor): a cursor to communicate with the database
        """
        conn = mysql.connector.connect(user=self._user, password=self._password, host=self._host, database=self._dbid)
        curs = conn.cursor()
        # Check db exists
        curs.execute("SHOW TABLES")
        if len(curs.fetchall()) == 0:
            # Database does not exist
            raise Exception("Requested Database %s does not exist" % self._dbid)
        return conn, curs

    def execute_query(self, query, retry=True):
        """Executes a query on the database, and returns all values

        Args:
            query (string): the SQL command to run

        Returns:
            values (list): list of all rows returned
        """

        try:
            self.open_connection_if_closed()
            self._curs.execute(query)
            values = self._curs.fetchall()
            return values
        except Exception as err:
            if retry:
                try:
                    self.reset_connection()
                    self.execute_query(query=query,retry=False)
                except Exception as reconnection_err:
                    err = reconnection_err
            raise Exception ("Error executing query: %s", err)

    def commit(self, query, retry=True):
        try:
            self.open_connection_if_closed()
            self._curs.execute(query)
            self._conn.commit()
        except Exception as err:
            if retry:
                try:
                    self.reset_connection()
                    self.execute_query(query=query,retry=False)
                except Exception as reconnection_err:
                    err = reconnection_err
            raise Exception ("Error updating database: %s", err)