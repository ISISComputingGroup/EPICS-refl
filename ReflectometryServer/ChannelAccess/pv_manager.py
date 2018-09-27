"""
Reflectometry pv manager
"""
from ReflectometryServer.parameters import BeamlineParameterType
from server_common.utilities import create_pv_name

PARAM_PREFIX = "PARAM:"
BEAMLINE_MODE = "BL:MODE"
BEAMLINE_MOVE = "BL:MOVE"
BEAMLINE_STATUS = "BL:STAT"
BEAMLINE_MESSAGE = "BL:MSG"
SP_SUFFIX = ":SP"
SP_RBV_SUFFIX = ":SP:RBV"
MOVE_SUFFIX = ":MOVE"
CHANGED_SUFFIX = ":CHANGED"
SET_AND_MOVE_SUFFIX = ":SETANDMOVE"

PARAMS_FIELDS = {
    BeamlineParameterType.IN_OUT: {'enums': ["OUT", "IN"]},
    BeamlineParameterType.FLOAT: {'prec': 3, 'value': 0.0}}


class PVManager:
    """
    Holds reflectometry PVs and associated utilities.
    """
    def __init__(self, param_types, mode_names, status_codes):
        """
        The constructor.
        Args:
            param_types (dict[str, str]): The types for which to create PVs, keyed by name.
            mode_names: names of the modes
        """
        self.PVDB = {
            BEAMLINE_MOVE: {
                'type': 'int',
                'count': 1,
                'value': 0,
            },
            BEAMLINE_MODE: {
                'type': 'enum',
                'enums': mode_names
            },
            BEAMLINE_STATUS: {
                'type': 'enum',
                'enums': status_codes
            },
            BEAMLINE_MESSAGE: {
                'type': 'string'
            },
        }

        self._pv_lookup = {}
        for param, param_type in param_types.items():
            self._add_parameter_pvs(param, **PARAMS_FIELDS[param_type])

        for pv_name in self.PVDB.keys():
            print("creating pv: {}".format(pv_name))

    def _add_parameter_pvs(self, param_name, **fields):
        """
        Adds all PVs needed for one beamline parameter to the PV database.

        :param param_name: The name of the beamline parameter
        :param fields: The fields of the parameter PV
        """
        try:
            param_alias = create_pv_name(param_name, self.PVDB.keys(), "PARAM")
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
