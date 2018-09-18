"""
Reflectometry pv manager
"""
from ReflectometryServer.parameters import BeamlineParameterType, TrackingPosition
from server_common.utilities import create_pv_name
import json

PARAM_PREFIX = "PARAM"
BEAMLINE_MODE = "BL:MODE"
BEAMLINE_MOVE = "BL:MOVE"
TRACKING_AXES = "TRACKING_AXES"
SP_SUFFIX = ":SP"
SP_RBV_SUFFIX = ":SP:RBV"
MOVE_SUFFIX = ":MOVE"
CHANGED_SUFFIX = ":CHANGED"
SET_AND_MOVE_SUFFIX = ":SETANDMOVE"

TRIGGER_FIELDS = {'type': 'int', 'count': 1, 'value': 0}
PARAMS_FIELDS = {
    BeamlineParameterType.IN_OUT: {'enums': ["OUT", "IN"]},
    BeamlineParameterType.FLOAT: {'prec': 3, 'value': 0.0}
}


class PVManager:
    """
    Holds reflectometry PVs and associated utilities.
    """
    def __init__(self, parameters, mode_names):
        """
        The constructor.
        Args:
            parameters (list[ReflectometryServer.parameters.BeamlineParameter]): The parameters for which to create PVs
            mode_names: names of the modes
        """
        self.PVDB = {
            BEAMLINE_MOVE: TRIGGER_FIELDS,
            BEAMLINE_MODE: {
                'type': 'enum',
                'enums': mode_names
            }
        }

        self._pv_lookup = {}
        self._position_params = {}
        for param in parameters:
            self._add_parameter_pvs(param, **PARAMS_FIELDS[param.parameter_type])
        self.PVDB[TRACKING_AXES] = {'type': 'char',
                                    'count': 300,
                                    'value': json.dumps(self._position_params)
                                    }
        for pv_name in self.PVDB.keys():
            print("creating pv: {}".format(pv_name))

    def _add_parameter_pvs(self, param, **fields):
        """
        Adds all PVs needed for one beamline parameter to the PV database.

        :param param_name: The name of the beamline parameter
        :param fields: The fields of the parameter PV
        """
        try:
            param_alias = create_pv_name(param.name, self.PVDB.keys(), "PARAM")
            prepended_alias = self.prepend_param(param_alias)
            self.PVDB[prepended_alias] = fields
            self.PVDB[prepended_alias + SP_SUFFIX] = fields
            self.PVDB[prepended_alias + SP_RBV_SUFFIX] = fields
            self.PVDB[prepended_alias + SET_AND_MOVE_SUFFIX] = fields
            self.PVDB[prepended_alias + CHANGED_SUFFIX] = {'type': 'enum',
                                                           'enums': ["NO", "YES"]}
            self.PVDB[prepended_alias + MOVE_SUFFIX] = TRIGGER_FIELDS
            self._pv_lookup[param_alias] = param.name
            if type(param) is TrackingPosition:
                self._position_params[param_alias] = param.name
        except Exception as err:
            print("Error adding parameter PV: " + err.message)

    def get_param_name_from_pv(self, pv):
        """
        Extracts the name of a beamline parameter based on its PV address.
        :param pv: The PV address
        :return: The parameter associated to the PV
        """
        delim = pv.split(":")
        if PARAM_PREFIX in delim:
            param_alias = delim[delim.index(PARAM_PREFIX) + 1]
        else:
            param_alias = delim[0]
        try:
            return self._pv_lookup[param_alias]
        except KeyError:
            print("Error: Could not find beamline parameter for alias " + param_alias)

    def parameter_pvs(self):
        """
        :return: The list of PVs of all beamline parameters.
        """
        return [self.prepend_param(pv_alias) for pv_alias in self._pv_lookup.keys()]

    @staticmethod
    def prepend_param(param):
        return PARAM_PREFIX + ":" + param
