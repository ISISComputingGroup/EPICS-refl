"""
Reflectometry pv manager
"""
from enum import Enum

from ReflectometryServer.parameters import BeamlineParameterType, BeamlineParameterGroup
from server_common.ioc_data_source import PV_INFO_FIELD_NAME, PV_DESCRIPTION_NAME
from server_common.utilities import create_pv_name, remove_from_end, print_and_log, SEVERITY
import json


PARAM_PREFIX = "PARAM"
BEAMLINE_PREFIX = "BL:"
BEAMLINE_MODE = BEAMLINE_PREFIX + "MODE"
BEAMLINE_MOVE = BEAMLINE_PREFIX + "MOVE"
BEAMLINE_STATUS = BEAMLINE_PREFIX + "STAT"
BEAMLINE_MESSAGE = BEAMLINE_PREFIX + "MSG"
TRACKING_AXES = "TRACKING_AXES"
SP_SUFFIX = ":SP"
SP_RBV_SUFFIX = ":SP:RBV"
MOVE_SUFFIX = ":MOVE"
CHANGED_SUFFIX = ":CHANGED"
SET_AND_NO_MOVE_SUFFIX = ":SP_NO_MOVE"
VAL_FIELD = ".VAL"

FOOTPRINT_PREFIX = "FP"

SAMPLE_LENGTH = "{}:{}".format(FOOTPRINT_PREFIX, "SAMPLE_LENGTH")
FP_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "FOOTPRINT")
DQQ_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "DQQ")
QMIN_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "QMIN")
QMAX_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "QMAX")

FP_SP_PREFIX = "SP"
FP_SP_RBV_PREFIX = "SP_RBV"
FP_RBV_PREFIX = "RBV"

FOOTPRINT_PREFIXES = [FP_SP_PREFIX, FP_SP_RBV_PREFIX, FP_RBV_PREFIX]

PARAM_FIELDS_CHANGED = {'type': 'enum', 'enums': ["NO", "YES"]}

PARAM_FIELDS_MOVE = {'type': 'int', 'count': 1, 'value': 0}

PARAMS_FIELDS_BEAMLINE_TYPES = {
    BeamlineParameterType.IN_OUT: {'enums': ["OUT", "IN"]},
    BeamlineParameterType.FLOAT: {'type': 'float', 'prec': 3, 'value': 0.0}}


class PvSort(Enum):
    """
    Enum for the type of PV
    """
    RBV = 0
    MOVE = 1
    SP_RBV = 2
    SP = 3
    SET_AND_NO_MOVE = 4
    CHANGED = 6

    @staticmethod
    def what(pv_sort):
        """
        Args:
            pv_sort: pv sort to determin

        Returns: what the pv sort does
        """
        if pv_sort == PvSort.RBV:
            return ""
        elif pv_sort == PvSort.MOVE:
            return "(Do move)"
        elif pv_sort == PvSort.SP_RBV:
            return "(Set point readback)"
        elif pv_sort == PvSort.SP:
            return "(Set point)"
        elif pv_sort == PvSort.SET_AND_NO_MOVE:
            return "(Set point with no move afterwards)"
        elif pv_sort == PvSort.CHANGED:
            return "(is changed)"
        else:
            print_and_log("Unknown pv sort!! {}".format(pv_sort), severity=SEVERITY.MAJOR, src="REFL")
            return "(unknown)"

    def get_from_parameter(self, parameter):
        """
        Get the value of the correct sort from a parameter
        Args:
            parameter(ReflectometryServer.parameters.BeamlineParameter): the parameter to get the value from

        Returns: the value of the parameter of the correct sort
        """
        if self == PvSort.SP:
            return parameter.sp
        elif self == PvSort.SP_RBV:
            return parameter.sp_rbv
        elif self == PvSort.CHANGED:
            return parameter.sp_changed
        elif self == PvSort.SET_AND_NO_MOVE:
            return parameter.sp_no_move
        elif self == PvSort.RBV:
            return parameter.rbv
        elif self == PvSort.MOVE:
            return parameter.move
        return None


class FootprintSort(Enum):
    """
    Enum for the type of footprint calculator
    """
    SP = 0
    RBV = 1
    SP_RBV = 2

    @staticmethod
    def prefix(sort):
        """
        Args:
            sort: The sort of footprint value

        Returns: The pv suffix for this sort of value
        """
        if sort == FootprintSort.SP:
            return FP_SP_PREFIX
        elif sort == FootprintSort.SP_RBV:
            return FP_SP_RBV_PREFIX
        elif sort == FootprintSort.RBV:
            return FP_RBV_PREFIX
        return None


class PVManager:
    """
    Holds reflectometry PVs and associated utilities.
    """
    def __init__(self, param_types, mode_names, status_codes):
        """
        The constructor.
        Args:
            param_types (dict[str, (str, str, str)]): The type, group name and description for which to create PVs,
                keyed by name.
            mode_names: The names of the modes in the current reflectometry configuration
            status_codes (list[ReflectometryServer.beamline.STATUS]): status codes of Beam line with severities
        """

        self.PVDB = {}
        self._params_pv_lookup = {}
        self._tracking_positions = {}
        self._footprint_parameters = {}

        self._add_global_pvs(mode_names, status_codes)
        self._add_footprint_calculator_pvs()
        self._add_all_parameter_pvs(param_types)

        for pv_name in self.PVDB.keys():
            print("creating pv: {}".format(pv_name))

    def _add_global_pvs(self, mode_names, status_codes):
        """
        Add PVs that affect the whole of the reflectometry system to the server's PV database.

        Args:
            mode_names: The names of the modes in the current reflectometry configuration
            status_codes (list[ReflectometryServer.beamline.STATUS]): status codes of Beam line with severities
        """
        self._add_pv_with_val(BEAMLINE_MOVE, None, PARAM_FIELDS_MOVE, "Move the beam line", PvSort.RBV, archive=True,
                              interest="HIGH")
        # PVs for mode
        mode_fields = {'type': 'enum', 'enums': mode_names}
        self._add_pv_with_val(BEAMLINE_MODE, None, mode_fields, "Beamline mode", PvSort.RBV, archive=True,
                              interest="HIGH")
        self._add_pv_with_val(BEAMLINE_MODE + SP_SUFFIX, None, mode_fields, "Beamline mode", PvSort.SP)

        # PVs for server status
        status_fields = {'type': 'enum',
                         'enums': [code.display_string for code in status_codes],
                         'states': [code.alarm_severity for code in status_codes]}
        self._add_pv_with_val(BEAMLINE_STATUS, None, status_fields, "Status of the beam line", PvSort.RBV, archive=True,
                              interest="HIGH", alarm=True)
        self._add_pv_with_val(BEAMLINE_MESSAGE, None, {'type': 'string'}, "Message about the beamline", PvSort.RBV,
                              archive=True, interest="HIGH")

    def _add_footprint_calculator_pvs(self):
        """
        Add PVs related to the footprint calculation to the server's PV database.
        """
        self._add_pv_with_val(SAMPLE_LENGTH, None, PARAMS_FIELDS_BEAMLINE_TYPES[BeamlineParameterType.FLOAT],
                              "Sample Length", PvSort.SP_RBV, archive=True, interest="HIGH")

        for prefix in FOOTPRINT_PREFIXES:
            for template, description in [(FP_TEMPLATE, "Beam Footprint"),
                                          (DQQ_TEMPLATE, "Beam Resolution dQ/Q"),
                                          (QMIN_TEMPLATE, "Minimum measurable Q with current setup"),
                                          (QMAX_TEMPLATE, "Maximum measurable Q with current setup")]:
                self._add_pv_with_val(template.format(prefix), None,
                                      PARAMS_FIELDS_BEAMLINE_TYPES[BeamlineParameterType.FLOAT],
                                      description, PvSort.RBV, archive=True, interest="HIGH")

    def _add_all_parameter_pvs(self, param_types):
        """
        Add PVs for each beamline parameter in the reflectometry configuration to the server's PV database.

        Args:
            param_types (dict[str, (str, str, str)]): The type, group name and description for which to create PVs,
                keyed by name.
        """
        for param, (param_type, group_names, description) in param_types.items():
            self._add_parameter_pvs(param, group_names, description, **PARAMS_FIELDS_BEAMLINE_TYPES[param_type])
        self.PVDB[TRACKING_AXES] = {'type': 'char',
                                    'count': 300,
                                    'value': json.dumps(self._tracking_positions)
                                    }

    def _add_parameter_pvs(self, param_name, group_names, description, **fields):
        """
        Adds all PVs needed for one beamline parameter to the PV database.

        Args:
            param_name: The name of the beamline parameter
            fields: The fields of the parameter PV
            group_names: list fo groups to which this parameter belong
            description: description of the pv
        """
        try:
            param_alias = create_pv_name(param_name, self.PVDB.keys(), "PARAM", limit=10)
            prepended_alias = "{}:{}".format(PARAM_PREFIX, param_alias)
            if BeamlineParameterGroup.TRACKING in group_names:
                self._tracking_positions[prepended_alias] = param_name

            self.PVDB["{}.DESC".format(prepended_alias)] = {'type': 'string',
                                                            'value': description
                                                            }

            # Readback PV
            self._add_pv_with_val(prepended_alias, param_name, fields, description, PvSort.RBV, archive=True,
                                  interest="HIGH")

            # Setpoint PV
            self._add_pv_with_val(prepended_alias + SP_SUFFIX, param_name, fields, description, PvSort.SP, archive=True)

            # Setpoint readback PV
            self._add_pv_with_val(prepended_alias + SP_RBV_SUFFIX, param_name, fields, description, PvSort.SP_RBV)

            # Set value and move PV
            self._add_pv_with_val(prepended_alias + SET_AND_NO_MOVE_SUFFIX, param_name, fields, description,
                                  PvSort.SET_AND_NO_MOVE)

            # Changed PV
            self._add_pv_with_val(prepended_alias + CHANGED_SUFFIX, param_name, PARAM_FIELDS_CHANGED, description,
                                  PvSort.CHANGED)

            # Move PV
            self._add_pv_with_val(prepended_alias + MOVE_SUFFIX, param_name, PARAM_FIELDS_MOVE, description,
                                  PvSort.MOVE)

        except Exception as err:
            print("Error adding parameter PV: " + err.message)

    def _add_pv_with_val(self, pv_name, param_name, pv_fields, description, sort, archive=False, interest=None,
                         alarm=False):
        """
        Add param to pv list with .val and correct fields and to parm look up
        Args:
            pv_name: name of the pv
            param_name: name of the parameter; None for not a parameter
            pv_fields: pv fields to use
            sort: sort of pv it is
            archive: True if it should be archived
            interest: level of interest; None is not interesting
            alarm: True if this pv represents the alarm state of the IOC; false otherwise

        Returns:

        """
        pv_fields = pv_fields.copy()
        pv_fields[PV_DESCRIPTION_NAME] = description + PvSort.what(sort)

        pv_fields_mod = pv_fields.copy()
        pv_fields_mod[PV_INFO_FIELD_NAME] = {}
        if interest is not None:
            pv_fields_mod[PV_INFO_FIELD_NAME]["INTEREST"] = interest
        if archive:
            pv_fields_mod[PV_INFO_FIELD_NAME]["archive"] = "VAL"
        if alarm:
            pv_fields_mod[PV_INFO_FIELD_NAME]["alarm"] = "Reflectometry IOC (REFL)"

        self.PVDB[pv_name] = pv_fields_mod
        self.PVDB[pv_name + VAL_FIELD] = pv_fields

        if param_name is not None:
            self._params_pv_lookup[pv_name] = (param_name, sort)

    def param_names_pvnames_and_sort(self):
        """

        Returns:
            (list[str, tuple[str, PvSort]]): The list of PVs of all beamline parameters.

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

    def get_param_name_and_sort_from_pv(self, pv_name):
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
        return self._is_pv_name_this_field(BEAMLINE_MOVE, pv_name)

    def is_tracking_axis(self, pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the beamline tracking axis pv
        """
        return self._is_pv_name_this_field(TRACKING_AXES, pv_name)

    def is_beamline_status(self, pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the beamline status pv
        """
        return self._is_pv_name_this_field(BEAMLINE_STATUS, pv_name)

    def is_beamline_message(self, pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the beamline message pv
        """
        return self._is_pv_name_this_field(BEAMLINE_MESSAGE, pv_name)

    def is_sample_length(self, pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the sample length pv
        """
        return self._is_pv_name_this_field(SAMPLE_LENGTH, pv_name)

    def _is_pv_name_this_field(self, field_name, pv_name):
        """

        Args:
            field_name: field name to match
            pv_name: pv name to match

        Returns: True if field name is pv name (with oe without VAL  field)

        """
        pvname_no_val = remove_from_end(pv_name, VAL_FIELD)
        return pvname_no_val == field_name
