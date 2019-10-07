from __future__ import print_function, absolute_import, division, unicode_literals
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

import json
import six
import unicodedata

from server_common.channel_access import ChannelAccess
from server_common.mysql_abstraction_layer import SQLAbstraction
from server_common.utilities import compress_and_hex, char_waveform


class User(object):
    """
    A user class to allow for easier conversions from database to json.
    """
    def __init__(self, name="UNKNOWN", institute="UNKNOWN", role="UNKNOWN"):
        self.name = name
        self.institute = institute
        self.role = role


class ExpDataSource(object):
    """
    This is a humble object containing all the code for accessing the database.
    """
    def __init__(self):
        self._db = SQLAbstraction('exp_data', "exp_data", "$exp_data")

    def get_team(self, experiment_id):
        """
        Gets the team members.

        Args:
            experiment_id (string): the id of the experiment to load related data from

        Returns:
            team (list): the team data found by the SQL query
        """
        try:
            sqlquery = "SELECT user.name, user.organisation, role.name"
            sqlquery += " FROM role, user, experimentteams"
            sqlquery += " WHERE role.roleID = experimentteams.roleID"
            sqlquery += " AND user.userID = experimentteams.userID"
            sqlquery += " AND experimentteams.experimentID = %s"
            sqlquery += " GROUP BY user.userID"
            sqlquery += " ORDER BY role.priority"
            team = [list(element) for element in self._db.query(sqlquery, (experiment_id,))]
            if len(team) == 0:
                raise Exception("unable to find team details for experiment ID %s" % experiment_id)
            else:
                return team
        except Exception as err:
            raise Exception("issue getting experimental team: %s" % err)

    def experiment_exists(self, experiment_id):
        """
        Gets the experiment.

        Args:
            experiment_id (string): the id of the experiment to load related data from

        Returns:
            exists (boolean): TRUE if the experiment exists, FALSE otherwise
        """
        try:
            sqlquery = "SELECT experiment.experimentID"
            sqlquery += " FROM experiment "
            sqlquery += " WHERE experiment.experimentID = %s"
            id = self._db.query(sqlquery, (experiment_id,))
            if len(id) >= 1:
                return True
            else:
                return False
        except Exception as err:
            raise Exception("error finding the experiment: %s" % err)


class ExpData(object):
    """
    A wrapper to connect to the IOC database via MySQL.
    """
    EDPV = {
        'ED:RBNUMBER:SP': char_waveform(16000),
        'ED:USERNAME:SP': char_waveform(16000)
    }

    _to_ascii = {}

    def __init__(self, prefix, db, ca=ChannelAccess):
        """
        Constructor.

        Args:
            prefix (string): The pv prefix of the instrument the server is being run on
            db (ExpDataSource): The source of the experiment data
            ca (ChannelAccess): The channel access server to use
        """
        # Build the PV names to be used
        self._simrbpv = prefix + "ED:SIM:RBNUMBER"
        self._daerbpv = prefix + "ED:RBNUMBER:DAE:SP"
        self._simnames = prefix + "ED:SIM:USERNAME"
        self._daenamespv = prefix + "ED:USERNAME:DAE:SP"
        self._surnamepv = prefix + "ED:SURNAME"
        self._orgspv = prefix + "ED:ORGS"

        # Set the channel access server to use
        self.ca = ca

        # Set the data source to use
        self._db = db

        # Create ascii mappings
        ExpData._to_ascii = self._make_ascii_mappings()

    @staticmethod
    def _make_ascii_mappings():
        """
        Create mapping for characters not converted to 7 bit by NFKD.
        """
        mappings_in = [ord(char) for char in u'\xd0\xd7\xd8\xde\xdf\xf0\xf8\xfe']
        mappings_out = u'DXOPBoop'
        d = dict(zip(mappings_in, mappings_out))
        d[ord(u'\xc6')] = u'AE'
        d[ord(u'\xe6')] = u'ae'
        return d

    def encode_for_return(self, data):
        """
        Converts data to JSON, compresses it and converts it to hex.

        Args:
            data (string): The data to encode

        Returns:
            string : The encoded data
        """
        return compress_and_hex(json.dumps(six.binary_type(data)).encode('utf-8', 'replace'))

    def _get_surname_from_fullname(self, fullname):
        try:
            return fullname.split(" ")[-1]
        except:
            return fullname

    def update_experiment_id(self, experiment_id):
        """
        Updates the associated PVs when an experiment ID is set.

        Args:
            experiment_id (string): the id of the experiment to load related data from

        Returns:
            None specifically, but the following information external to the server is set
            # TODO: Update with the correct PVs for this part

        """
        # Update the RB Number for lookup - SIM for testing, DAE for production
        self.ca.caput(self._simrbpv, experiment_id)
        self.ca.caput(self._daerbpv, experiment_id)

        # Check for the experiment ID
        names = []
        surnames = []
        orgs = []

        if not self._db.experiment_exists(experiment_id):
            self.ca.caput(self._simnames, self.encode_for_return(names))
            self.ca.caput(self._surnamepv, self.encode_for_return(surnames))
            self.ca.caput(self._orgspv, self.encode_for_return(orgs))
            raise Exception("error finding the experiment: %s" % experiment_id)

        # Get the user information from the database and update the associated PVs
        if self._db is not None:
            teammembers = self._db.get_team(experiment_id)
            # Generate the lists/similar for conversion to JSON
            for member in teammembers:
                fullname = six.text_type(member[0])
                org = six.text_type(member[1])
                role = six.text_type(member[2])
                if not role == "Contact":
                    surnames.append(self._get_surname_from_fullname(fullname))
                orgs.append(org)
                name = User(fullname, org, role.lower())
                names.append(name.__dict__)
            orgs = list(set(orgs))
            self.ca.caput(self._simnames, self.encode_for_return(names))
            self.ca.caput(self._surnamepv, self.encode_for_return(surnames))
            self.ca.caput(self._orgspv, self.encode_for_return(orgs))
            # The value put to the dae names pv will need changing in time to use compressed and hexed json etc. but
            # this is not available at this time in the ICP
            self.ca.caput(self._daenamespv, ExpData.make_name_list_ascii(surnames))

    def update_username(self, users):
        """
        Updates the associated PVs when the User Names are altered.

        Args:
            users (string): uncompressed and dehexed json string with the user details

        Returns:
            None specifically, but the following information external to the server is set
            # TODO: Update with the correct PVs for this part
        """
        names = []
        surnames = []
        orgs = []
        if len(users) > 3:
            # Format the string into a list of JSON strings for decoding/encoding
            users = users[1:-1]
            users = users.split("},{")
            if len(users) > 1:
                # Strip the {} from the beginning and the end to allow for easier editing of the teammembers
                users[0] = users[0][1:]
                users[-1] = users[-1][:len(users[-1])-1]
                # Add a {} to EACH teammember
                for ndx, member in enumerate(users):
                    users[ndx] = "{" + member + "}"

            # Loop through the list of strings to generate the lists/similar for conversion to JSON
            for teammember in users:
                member = json.loads(teammember)
                fullname = six.text_type(member['name'])
                org = six.text_type(member['institute'])
                role = six.text_type(member['role'])
                if not role == "Contact":
                    surnames.append(self._get_surname_from_fullname(fullname))
                orgs.append(org)
                name = User(fullname, org, role.lower())
                names.append(name.__dict__)
            orgs = list(set(orgs))
        self.ca.caput(self._simnames, self.encode_for_return(names))
        self.ca.caput(self._surnamepv, self.encode_for_return(surnames))
        self.ca.caput(self._orgspv, self.encode_for_return(orgs))
        # The value put to the dae names pv will need changing in time to use compressed and hexed json etc. but
        # this is not available at this time in the ICP
        if not surnames:
            self.ca.caput(self._daenamespv, " ")
        else:
            self.ca.caput(self._daenamespv, ExpData.make_name_list_ascii(surnames))

    @staticmethod
    def make_name_list_ascii(names):
        """
        Takes a unicode list of names and creates a best ascii comma separated list this implementation is a temporary
        fix until we install the PyPi unidecode module.
        
        Args:
            name(list): list of unicode names

        Returns:
            comma separated ascii string of names with special characters adjusted
        """
        nlist = u','.join(names)
        nfkd_form = unicodedata.normalize('NFKD', nlist)
        nlist_no_sc = u''.join([c for c in nfkd_form if not unicodedata.combining(c)])
        return nlist_no_sc.translate(ExpData._to_ascii).encode('ascii', 'ignore')
