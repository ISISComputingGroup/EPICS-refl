"""
Reflectometry pv manager
"""
from ReflectometryServer.parameters import BeamlineParameterType
from server_common.ioc_data_source import PV_INFO_FIELD_NAME
from server_common.utilities import create_pv_name

PARAM_PREFIX = "PARAM:"
BEAMLINE_MODE = "BL:MODE"
BEAMLINE_MOVE = "BL:MOVE"
SP_SUFFIX = ":SP"
SP_RBV_SUFFIX = ":SP:RBV"
MOVE_SUFFIX = ":MOVE"
CHANGED_SUFFIX = ":CHANGED"
SET_AND_MOVE_SUFFIX = ":SETANDMOVE"
VAL_FIELD = ".VAL"

PARAM_FIELDS_CHANGED = {'type': 'enum', 'enums': ["NO", "YES"]}

PARAM_FIELDS_MOVE = {'type': 'int', 'count': 1, 'value': 0, }

PARAMS_FIELDS_BEAMLINE_TYPES = {
    BeamlineParameterType.IN_OUT: {'enums': ["OUT", "IN"]},
    BeamlineParameterType.FLOAT: {'type': 'float', 'prec': 3, 'value': 0.0}}

ARCHIVED = {
    "archive": "VAL",
}

INTERESTING_AND_ARCHIVED = {
    "archive": "VAL",
    "INTEREST": "HIGH"
}


class PVManager:
    """
    Holds reflectometry PVs and associated utilities.
    """
    def __init__(self, param_types, mode_names):
        """
        The constructor.
        Args:
            param_types (dict[str, str]): The types for which to create PVs, keyed by name.
            mode_names: names of the modes
        """

        mode_fields = {'type': 'enum', 'enums': mode_names, PV_INFO_FIELD_NAME: INTERESTING_AND_ARCHIVED}
        self.PVDB = {
            BEAMLINE_MOVE: PARAM_FIELDS_MOVE,
            BEAMLINE_MOVE + VAL_FIELD: PARAM_FIELDS_MOVE,
            BEAMLINE_MODE: mode_fields,
            BEAMLINE_MODE + VAL_FIELD: mode_fields,
            BEAMLINE_MODE + SP_SUFFIX: mode_fields,
            BEAMLINE_MODE + SP_SUFFIX + VAL_FIELD: mode_fields
        }

        self._pv_lookup = {}
        for param, param_type in param_types.items():
            self._add_parameter_pvs(param, "", **PARAMS_FIELDS_BEAMLINE_TYPES[param_type])

        for pv_name in self.PVDB.keys():
            print("creating pv: {}".format(pv_name))

    def _add_parameter_pvs(self, param_name, field_name, **fields):
        """
        Adds all PVs needed for one beamline parameter to the PV database.

        :param param_name: The name of the beamline parameter
        :param fields: The fields of the parameter PV
        """
        try:
            param_alias = create_pv_name(param_name, self.PVDB.keys(), "PARAM")
            self._pv_lookup[param_alias + field_name] = param_name

            prepended_alias = PARAM_PREFIX + param_alias
            field_with_intrest_and_archiving = fields.copy()
            field_with_intrest_and_archiving[PV_INFO_FIELD_NAME] = INTERESTING_AND_ARCHIVED

            field_with_intrest_and_archiving[PV_INFO_FIELD_NAME + VAL_FIELD] = fields
            fields_with_archiving = fields.copy()
            fields_with_archiving[PV_INFO_FIELD_NAME] = ARCHIVED
            # Readback PV
            self.PVDB[prepended_alias + field_name] = field_with_intrest_and_archiving
            self.PVDB[prepended_alias + field_name + VAL_FIELD] = fields

            # Setpoint PV
            self.PVDB[prepended_alias + SP_SUFFIX + field_name] = fields_with_archiving
            self.PVDB[prepended_alias + SP_SUFFIX + field_name + VAL_FIELD] = fields

            # Setpoint readback PV
            self.PVDB[prepended_alias + SP_RBV_SUFFIX + field_name] = fields
            self.PVDB[prepended_alias + SP_RBV_SUFFIX + field_name + VAL_FIELD] = fields

            # Set value and move PV
            self.PVDB[prepended_alias + SET_AND_MOVE_SUFFIX + field_name] = fields
            self.PVDB[prepended_alias + SET_AND_MOVE_SUFFIX + field_name + VAL_FIELD] = fields

            # Changed PV
            self.PVDB[prepended_alias + CHANGED_SUFFIX + field_name] = PARAM_FIELDS_CHANGED
            self.PVDB[prepended_alias + CHANGED_SUFFIX + field_name + VAL_FIELD] = PARAM_FIELDS_CHANGED

            # Move  PV
            self.PVDB[prepended_alias + MOVE_SUFFIX + field_name] = PARAM_FIELDS_MOVE
            self.PVDB[prepended_alias + MOVE_SUFFIX + field_name + VAL_FIELD] = PARAM_FIELDS_MOVE

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
