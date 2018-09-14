import re


PARAM_PREFIX = "PARAM:"
BEAMLINE_MODE = "BL:MODE"
BEAMLINE_MOVE = "BL:MOVE"
SP_SUFFIX = ":SP"
SP_RBV_SUFFIX = ":SP:RBV"
MOVE_SUFFIX = ":MOVE"
CHANGED_SUFFIX = ":CHANGED"
SET_AND_MOVE_SUFFIX = ":SETANDMOVE"


class PVManager:
    """
    Holds reflectometry PVs and associated utilities.
    """
    def __init__(self, params_fields, modes):
        """
        The constructor.
        :param params_fields: The parameters for which to create PVs and their PV fields.
        """
        self.PVDB = {
            BEAMLINE_MOVE: {
                'type': 'int',
                'count': 1,
                'value': 0,
            },
            BEAMLINE_MODE: {
                'type': 'enum',
                'enums': modes
            }
        }

        self._pv_lookup = {}
        for param, fields in params_fields.iteritems():
            self._add_parameter_pvs(param, **fields)

    def _add_parameter_pvs(self, param_name, **fields):
        """
        Adds all PVs needed for one beamline parameter to the PV database.

        :param param_name: The name of the beamline parameter
        :param fields: The fields of the parameter PV
        """
        try:
            param_alias = self.create_pv_alias(param_name, "PARAM")
            prepended_alias = PARAM_PREFIX + param_alias
            self.PVDB[prepended_alias] = fields
            self.PVDB[prepended_alias + SP_SUFFIX] = fields
            self.PVDB[prepended_alias + SP_RBV_SUFFIX] = fields
            self.PVDB[prepended_alias + SET_AND_MOVE_SUFFIX] = fields
            self.PVDB[prepended_alias + CHANGED_SUFFIX] = {'type': 'enum',
                                                           'enums': ["NO", "YES"]}
            self.PVDB[prepended_alias + MOVE_SUFFIX] = {'type': 'int',
                                                        'count': 1,
                                                        'value': 0,
                                                        }
            self._pv_lookup[param_alias] = param_name
        except Exception as err:
            print("Error adding parameter PV: " + err.message)

    # TODO get this from blockserver utilities instead
    def create_pv_alias(self, name, default_pv, limit=6):
        """Uses the given name as a basis for a valid PV limited to a number of characters.

        Args:
            name (string): The basis for the PV
            default_pv (string): Basis for the PV if name is unreasonable, must be a valid PV name
            limit (integer): Character limit for the PV

        Returns:
            string : A valid PV
        """
        pv_text = name.upper().replace(" ", "_")
        pv_text = re.sub(r'\W', '', pv_text)
        # Check some edge cases of unreasonable names
        if re.search(r"[^0-9_]", pv_text) is None or pv_text == '':
            pv_text = default_pv

        # Ensure PVs aren't too long for the 60 character limit
        if pv_text > limit:
            pv_text = pv_text[0:limit]

        # Make sure PVs are unique
        i = 1
        pv = pv_text

        # Append a number if the PV already exists
        while pv in self.PVDB.keys():
            if len(pv) > limit - 2:
                pv = pv[0:limit - 2]
            pv += format(i, '02d')
            i += 1

        return pv

    def get_param_name_from_pv(self, pv):
        """
        Extracts the name of a beamline parameter based on its PV address.
        :param pv: The PV address
        :return: The parameter associated to the PV
        """
        param_alias = pv.split(":")[1]
        try:
            return self._pv_lookup[param_alias]
        except KeyError:
            print("Error: Could not find beamline parameter for alias " + param_alias)

    def parameter_pvs(self):
        """
        :return: The list of PVs of all beamline parameters.
        """
        return [PARAM_PREFIX + pv_alias for pv_alias in self._pv_lookup.keys()]
