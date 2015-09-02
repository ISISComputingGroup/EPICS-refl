from mysql_abstraction_layer import SQLAbstraction
from server_common.channel_access import caput
from server_common.utilities import compress_and_hex
import json

from server_common.utilities import compress_and_hex, print_and_log, convert_to_json

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

    def __init__(self, prefix):
        """Constructor

        Args:
            dbid (string) : The id of the database that holds IOC information
            prefix (string) : The pv prefix of the instrument the server is being run on
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

    def check_db_okay(self):
        """Attempts to connect to the database and raises an error if not able to do so
        """
        self._db.check_db_okay()

    # def __open_connection(self):
    #     return self._db.__open_connection()

    def _get_team(self, experimentID):
        """Gets the team members

        Args:
            experimentID (string) : the id of the experiment to load related data from

        Returns:
            team (list) : the team data found by the SQL query
        """
        try:
            sqlquery = "SELECT user.name, user.organisation, role.name"
            sqlquery += " FROM role, user, experimentteams"
            sqlquery += " WHERE role.roleID = experimentteams.roleID"
            sqlquery += " AND user.userID = experimentteams.userID"
            sqlquery += " AND experimentteams.experimentID = %s" % experimentID
            sqlquery += " ORDER BY role.priority"
            team = [list(element) for element in self._db.execute_query(sqlquery)]
            if len(team) == 0:
                raise Exception("unable to find team details for experiment ID %s" % experimentID)
            else:
                return team
        except Exception as err:
            raise Exception("issue getting experimental team: %s" % err)

    def _check_experiment_exists(self, experimentID):
        """ Gets the experiment

        Args:
            experimentID (string) : the id of the experiment to load related data from

        Returns:
            exists (boolean): TRUE if the experiment exists, FALSE otherwise
        """
        try:
            sqlquery = "SELECT experiment.experimentID"
            sqlquery += " FROM experiment "
            sqlquery += " WHERE experiment.experimentID = \"%s\"" % experimentID
            id = self._db.execute_query(sqlquery)
            if len(id) >= 1:
                return True
            else:
                return False
        except Exception as err:
            raise Exception("error finding the experiment: %s" % err)

    def encode4return(self, data):
        """Converts data to JSON, compresses it and converts it to hex.

        Args:
            data (string) : The data to encode

        Returns:
            string : The encoded data
        """
        return compress_and_hex(json.dumps(data).encode('ascii', 'replace'))

    def updateExperimentID(self, experimentID):
        """Updates the associated PVs when an experiment ID is set

        Args:
            experimentID (string) : the id of the experiment to load related data from

        Returns:
            None specifically, but the following information external to the server is set
            # TODO: Update with the correct PVs for this part

        """
        # Update the RB Number for lookup - SIM for testing, DAE for production
        caput(self._simrbpv, experimentID)
        caput(self._daerbpv, experimentID)
        # Check for the experiment ID
        idExists = self._check_experiment_exists(experimentID)
        if idExists == False:
            names = []
            surnames = []
            orgs = []
            caput(self._simnames, self.encode4return(names))
            caput(self._surnamepv, self.encode4return(surnames))
            caput(self._orgspv, self.encode4return(orgs))
            raise Exception("error finding the experiment: %s" % experimentID)
        # Get the user information from the database and update the associated PVs
        names = []
        surnames = []
        orgs = []
        if self._db is not None:
            teammembers = self._get_team(experimentID)
            if teammembers is not None:
                # Generate the lists/similar for conversion to JSON
                for member in teammembers:
                    fullname = str(member[0])
                    org = str(member[1])
                    role = str(member[2])
                    try:
                        surname = fullname.split(" ")[2]
                    except:
                        surname = fullname
                    if not role == "Contact":
                        surnames.append(surname)
                    orgs.append(org)
                    name = user(fullname, org, role.lower())
                    names.append(name.__dict__)
            orgs = list(set(orgs))
            caput(self._simnames, self.encode4return(names))
            caput(self._surnamepv, self.encode4return(surnames))
            caput(self._orgspv, self.encode4return(orgs))
            # The value put to the dae names pv will need changing in time to use compressed and hexed json etc. but
            # this is not available at this time in the ICP
            caput(self._daenamespv, ",".join(surnames))

    def updateUsername(self, users):
        """Updates the associated PVs when the User Names are altered

        Args:
            users (string) : uncompressed and dehexed json string with the user details

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
                fullname = str(member['name'])
                org = str(member['institute'])
                role = str(member['role'])
                try:
                    surname = fullname.split(" ")[2]
                except:
                    surname = fullname
                if not role == "Contact":
                    surnames.append(surname)
                orgs.append(org)
                name = user(fullname, org, role.lower())
                names.append(name.__dict__)
            orgs = list(set(orgs))
            caput(self._simnames, self.encode4return(names))
            caput(self._surnamepv, self.encode4return(surnames))
            caput(self._orgspv, self.encode4return(orgs))
            # The value put to the dae names pv will need changing in time to use compressed and hexed json etc. but
            # this is not available at this time in the ICP
            caput(self._daenamespv, ",".join(surnames))