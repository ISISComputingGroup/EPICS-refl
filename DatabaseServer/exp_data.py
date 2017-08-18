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
import unicodedata

from server_common.channel_access import ChannelAccess
from server_common.mysql_abstraction_layer import SQLAbstraction
from server_common.utilities import compress_and_hex

EDDB = 'exp_data'

class user(object):
    """A user class to allow for easier conversions from database to json"""
    def __init__(self, name="UNKNOWN", institute="UNKNOWN", role="UNKNOWN"):
        self.name = name
        self.institute = institute
        self.role = role


class ExpData(object):
    """A wrapper to connect to the IOC database via MySQL"""

    """Constant list of PVs to use"""
    EDPV = {
        'ED:RBNUMBER:SP': {
            'type': 'char',
            'count': 16000,
            'value': [0],
        },
        'ED:USERNAME:SP': {
            'type': 'char',
            'count': 16000,
            'value': [0],
        },
    }

    def make_ascii_mappings():
        """create mapping for characters not converted to 7 bit by NFKD"""
        mappings_in = [ ord(char) for char in u'\xd0\xd7\xd8\xde\xdf\xf0\xf8\xfe' ]
        mappings_out = u'DXOPBoop'
        d = dict(zip(mappings_in, mappings_out))
        d[ord(u'\xc6')] = u'AE'
        d[ord(u'\xe6')] = u'ae'
        return d

    _toascii = make_ascii_mappings()

    def __init__(self, prefix, ca=ChannelAccess):
        """Constructor

        Args:
            dbid (string): The id of the database that holds IOC information
            prefix (string): The pv prefix of the instrument the server is being run on
        """
        # Set up the database connection
        self._db = SQLAbstraction('exp_data', "exp_data", "$exp_data")

        # Build the PV names to be used
        self._simrbpv = prefix + "ED:SIM:RBNUMBER"
        self._daerbpv = prefix + "ED:RBNUMBER:DAE:SP"
        self._simnames = prefix + "ED:SIM:USERNAME"
        self._daenamespv = prefix + "ED:USERNAME:DAE:SP"
        self._surnamepv = prefix + "ED:SURNAME"
        self._orgspv = prefix + "ED:ORGS"

        # Set the channel access server to use
        self.ca = ca

    # def __open_connection(self):
    #     return self._db.__open_connection()

    def _get_team(self, experimentID):
        """Gets the team members

        Args:
            experimentID (string): the id of the experiment to load related data from

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
            team = [list(element) for element in self._db.query(sqlquery, (experimentID, ))]
            if len(team) == 0:
                raise Exception("unable to find team details for experiment ID %s" % experimentID)
            else:
                return team
        except Exception as err:
            raise Exception("issue getting experimental team: %s" % err)

    def _experiment_exists(self, experimentID):
        """ Gets the experiment

        Args:
            experimentID (string): the id of the experiment to load related data from

        Returns:
            exists (boolean): TRUE if the experiment exists, FALSE otherwise
        """
        try:
            sqlquery = "SELECT experiment.experimentID"
            sqlquery += " FROM experiment "
            sqlquery += " WHERE experiment.experimentID = %s"
            id = self._db.query(sqlquery, (experimentID,))
            if len(id) >= 1:
                return True
            else:
                return False
        except Exception as err:
            raise Exception("error finding the experiment: %s" % err)

    def encode4return(self, data):
        """Converts data to JSON, compresses it and converts it to hex.

        Args:
            data (string): The data to encode

        Returns:
            string : The encoded data
        """
        return compress_and_hex(json.dumps(data).encode('utf-8', 'replace'))

    def _get_surname_from_fullname(self, fullname):
        try:
            return fullname.split(" ")[-1]
        except:
            return fullname

    def updateExperimentID(self, experimentID):
        """Updates the associated PVs when an experiment ID is set

        Args:
            experimentID (string): the id of the experiment to load related data from

        Returns:
            None specifically, but the following information external to the server is set
            # TODO: Update with the correct PVs for this part

        """
        # Update the RB Number for lookup - SIM for testing, DAE for production
        self.ca.caput(self._simrbpv, experimentID)
        self.ca.caput(self._daerbpv, experimentID)

        # Check for the experiment ID
        names = []
        surnames = []
        orgs = []

        if not self._experiment_exists(experimentID):
            self.ca.caput(self._simnames, self.encode4return(names))
            self.ca.caput(self._surnamepv, self.encode4return(surnames))
            self.ca.caput(self._orgspv, self.encode4return(orgs))
            raise Exception("error finding the experiment: %s" % experimentID)

        # Get the user information from the database and update the associated PVs
        if self._db is not None:
            teammembers = self._get_team(experimentID)
            if teammembers is not None:
                # Generate the lists/similar for conversion to JSON
                for member in teammembers:
                    fullname = unicode(member[0])
                    org = unicode(member[1])
                    role = unicode(member[2])
                    if not role == "Contact":
                        surnames.append(self._get_surname_from_fullname(fullname))
                    orgs.append(org)
                    name = user(fullname, org, role.lower())
                    names.append(name.__dict__)
            orgs = list(set(orgs))
            self.ca.caput(self._simnames, self.encode4return(names))
            self.ca.caput(self._surnamepv, self.encode4return(surnames))
            self.ca.caput(self._orgspv, self.encode4return(orgs))
            # The value put to the dae names pv will need changing in time to use compressed and hexed json etc. but
            # this is not available at this time in the ICP
            self.ca.caput(self._daenamespv, ExpData.make_name_list_ascii(surnames))

    def updateUsername(self, users):
        """Updates the associated PVs when the User Names are altered

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
                fullname = unicode(member['name'])
                org = unicode(member['institute'])
                role = unicode(member['role'])
                if not role == "Contact":
                    surnames.append(self._get_surname_from_fullname(fullname))
                orgs.append(org)
                name = user(fullname, org, role.lower())
                names.append(name.__dict__)
            orgs = list(set(orgs))
        self.ca.caput(self._simnames, self.encode4return(names))
        self.ca.caput(self._surnamepv, self.encode4return(surnames))
        self.ca.caput(self._orgspv, self.encode4return(orgs))
        # The value put to the dae names pv will need changing in time to use compressed and hexed json etc. but
        # this is not available at this time in the ICP
        if not surnames:
            self.ca.caput(self._daenamespv, " ")
        else:
            self.ca.caput(self._daenamespv, ExpData.make_name_list_ascii(surnames))

    @staticmethod
    def make_name_list_ascii(names):
        """Takes a unicode list of names and creates a best ascii comma separated list
            this implementation is a temporary fix until we install the PyPi unidecode module
        
            Args:
                name(list): list of unicode names
            
            Returns:
                comma separated ascii string of names with special characters adjusted
                
        """
        nlist = u','.join(names)
        nfkd_form = unicodedata.normalize('NFKD', nlist)
        nlist_no_sc = u''.join([c for c in nfkd_form if not unicodedata.combining(c)])
        return nlist_no_sc.translate(ExpData._toascii).encode('ascii','ignore')
