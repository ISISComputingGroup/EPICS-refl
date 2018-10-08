"""
Abstracting out the sql connection.
"""
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


class DatabaseError(Exception):
    """
    Exception that is thrown if there is a problem with the database
    """
    def __init__(self, message):
        self.message = message


class AbstratSQLCommands(object):
    """
    Abstract base class for sql commands for testing
    """
    @staticmethod
    def generate_in_binding(parameter_count):
        """
        Generate a list of python sql bindings for use in a sql in clause. One binding for each parameter.
        i.e. %s, %s, %s for 3 parameters.

        Args:
            parameter_count: number of items in the in clause

        Returns: in binding

        """
        return ", ".join(["%s"] * parameter_count)

    def query_returning_cursor(self, command, bound_variables):
        """
        Generator which returns rows from query.
        Args:
            command: command to run
            bound_variables: any bound variables

        Yields: a row from the querry

        """
        raise NotImplemented()

    def _execute_command(self, command, is_query, bound_variables):
        """Executes a command on the database, and returns all values

        Args:
            command (string): the SQL command to run
            is_query (boolean): is this a query (i.e. do we expect return values)

        Returns:
            values (list): list of all rows returned. None if not is_query
        """
        raise NotImplementedError()

    def query(self, command, bound_variables=None):
        """Executes a query on the database, and returns all values

        Args:
            command (string): the SQL command to run
            bound_variables (tuple|dict): a tuple of parameters to bind into the query; Default no parameters to bind

        Returns:
            values (list): list of all rows returned
        """
        return self._execute_command(command, True, bound_variables)

    def update(self, command, bound_variables=None):
        """Executes an update on the database, and returns all values

        Args:
            command (string): the SQL command to run
            bound_variables (tuple|dict): a tuple of parameters to bind into the query; Default no parameters to bind
        """
        self._execute_command(command, False, bound_variables)


class SQLAbstraction(AbstratSQLCommands):
    """
    A wrapper to connect to MySQL databases.
    """

    # Number of available simultaneous connections to each connection pool
    POOL_SIZE = 16

    def __init__(self, dbid, user, password, host="127.0.0.1"):
        """
        Constructor.

        Args:
            dbid (string): The id of the database that holds the required information
            user (string): The username to use to connect to the database
            password (string): The password to use to connect to the database
            host (string): The host address to use, defaults to local host
        """
        super(SQLAbstraction, self).__init__()
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

    def _execute_command(self, command, is_query, bound_variables):
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
            curs.execute(command, bound_variables)
            if is_query:
                values = curs.fetchall()
            # Commit as part of the query or results won't be updated between subsequent transactions. Can lead
            # to values not auto-updating in the GUI.
            conn.commit()
        except Exception as err:
            print_and_log("Error executing command on database: {0}".format(err), "MAJOR")
            raise DatabaseError(str(err))
        finally:
            if curs is not None:
                curs.close()
            if conn is not None:
                conn.close()
        return values

    def query_returning_cursor(self, command, bound_variables):
        """
        Generator which returns rows from query.
        Args:
            command: command to run
            bound_variables: any bound variables

        Yields: a row from the querry

        """

        conn = None
        curs = None
        try:
            conn = self._get_connection()
            curs = conn.cursor()
            curs.execute(command, bound_variables)

            for row in curs:
                yield row

            # Commit as part of the query or results won't be updated between subsequent transactions. Can lead
            # to values not auto-updating in the GUI.
            conn.commit()
        except Exception as err:
            print_and_log("Error executing command on database: {0}".format(err), "MAJOR")
            raise DatabaseError(str(err))
        finally:
            if curs is not None:
                curs.close()
            if conn is not None:
                conn.close()
