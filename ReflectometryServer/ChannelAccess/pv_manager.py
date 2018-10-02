"""
Reflectometry pv manager
"""
from enum import Enum

from ReflectometryServer.parameters import BeamlineParameterType, BeamlineParameterGroup
from server_common.ioc_data_source import PV_INFO_FIELD_NAME
from server_common.utilities import create_pv_name, remove_from_end
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
VAL_FIELD = ".VAL"

PARAM_FIELDS_CHANGED = {'type': 'enum', 'enums': ["NO", "YES"]}

PARAM_FIELDS_MOVE = {'type': 'int', 'count': 1, 'value': 0, }
TRIGGER_FIELDS = {'type': 'int', 'count': 1, 'value': 0}

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


class PvSort(Enum):
    """
    Enum for the type of PV
    """
    RBV = 0
    MOVE = 1
    SP_RBV = 2
    SP = 3
    SET_AND_MOVE = 4
    CHANGED = 6


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

        self._params_pv_lookup = {}
        self._tracking_positions = {}
        for param, (param_type, group_names) in param_types.items():
            self._add_parameter_pvs(param, group_names, **PARAMS_FIELDS_BEAMLINE_TYPES[param_type])
        self.PVDB[TRACKING_AXES] = {'type': 'char',
                                    'count': 300,
                                    'value': json.dumps(self._tracking_positions)
                                    }
        for pv_name in self.PVDB.keys():
            print("creating pv: {}".format(pv_name))

    def _add_parameter_pvs(self, param_name, group_names, **fields):
        """
        Adds all PVs needed for one beamline parameter to the PV database.

        Args:
            param_name: The name of the beamline parameter
            fields: The fields of the parameter PV
            group_names: list fo groups to which this parameter belong
        """
        try:
            param_alias = create_pv_name(param_name, self.PVDB.keys(), "PARAM")
            prepended_alias = "{}:{}".format(PARAM_PREFIX, param_alias)
            if BeamlineParameterGroup.TRACKING in group_names:
                self._tracking_positions[prepended_alias] = param_name

            field_with_intrest_and_archiving = fields.copy()
            field_with_intrest_and_archiving[PV_INFO_FIELD_NAME] = INTERESTING_AND_ARCHIVED

            field_with_intrest_and_archiving[PV_INFO_FIELD_NAME + VAL_FIELD] = fields
            fields_with_archiving = fields.copy()
            fields_with_archiving[PV_INFO_FIELD_NAME] = ARCHIVED
            # Readback PV
            self._add_pv_with_val(prepended_alias, param_name, field_with_intrest_and_archiving, fields, PvSort.RBV)

            # Setpoint PV
            self._add_pv_with_val(prepended_alias + SP_SUFFIX, param_name, fields_with_archiving, fields, PvSort.SP)

            # Setpoint readback PV
            self._add_pv_with_val(prepended_alias + SP_RBV_SUFFIX, param_name, fields, fields, PvSort.SP_RBV)

            # Set value and move PV
            self._add_pv_with_val(prepended_alias + SET_AND_MOVE_SUFFIX, param_name,
                                  fields, fields, PvSort.SET_AND_MOVE)

            # Changed PV
            self._add_pv_with_val(prepended_alias + CHANGED_SUFFIX, param_name,
                                  PARAM_FIELDS_CHANGED, PARAM_FIELDS_CHANGED, PvSort.CHANGED)

            # Move  PV
            self._add_pv_with_val(prepended_alias + MOVE_SUFFIX, param_name,
                                  PARAM_FIELDS_MOVE, PARAM_FIELDS_MOVE, PvSort.MOVE)

        except Exception as err:
            print("Error adding parameter PV: " + err.message)

    def _add_pv_with_val(self, pv_name, param_name, pv_fields, pv_with_val_fields, param_sort):
        self.PVDB[pv_name] = pv_fields
        self.PVDB[pv_name + VAL_FIELD] = pv_with_val_fields
        self._params_pv_lookup[pv_name] = (param_name, param_sort)

    def param_names_pvnames_and_sort(self):
        """
        :return: The list of PVs of all beamline parameters.
        """
        return self._params_pv_lookup.items()

    def is_param(self, pv_name):
        """

        Args:
            pv_name: name of the pv

        Returns:
            True if the pv is a pv for beamline parameter
        """
        return remove_from_end(pv_name, VAL_FIELD) in self._params_pv_lookup

    def get_param_name_and_suffix_from_pv(self, pv_name):
        """
        Args:
            pv_name: name of pv to find

        Returns:
            (str, PvSort): parameter name and sort for the given pv
        """
        return self._params_pv_lookup[remove_from_end(pv_name, VAL_FIELD)]

    def is_beamline_mode(self, pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the beamline mode pv
        """
        pvname_no_val = remove_from_end(pv_name, VAL_FIELD)
        return pvname_no_val == BEAMLINE_MODE or pvname_no_val == BEAMLINE_MODE + SP_SUFFIX

    def is_beamline_move(self, pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the beamline move pv
        """
        pvname_no_val = remove_from_end(pv_name, VAL_FIELD)
        return pvname_no_val == BEAMLINE_MOVE

    def is_tracking_axis(self, pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the beamline tracking axis pv
        """
        pvname_no_val = remove_from_end(pv_name, VAL_FIELD)
        return pvname_no_val == TRACKING_AXES
