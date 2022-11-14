"""
Reflectometry pv manager
"""
import logging
from typing import Optional

from pcaspy import Severity

import ReflectometryServer
from ReflectometryServer.ChannelAccess.constants import STANDARD_FLOAT_PV_FIELDS
from ReflectometryServer.ChannelAccess.driver_utils import PvSort, \
    PARAMS_FIELDS_BEAMLINE_TYPES
from ReflectometryServer.server_status_manager import STATUS, STATUS_MANAGER, ProblemInfo
from ReflectometryServer.footprint_manager import FP_SP_KEY, FP_SP_RBV_KEY, FP_RBV_KEY
from pcaspy.alarm import SeverityStrings
from ReflectometryServer.parameters import BeamlineParameterType, BeamlineParameterGroup
from server_common.ioc_data_source import PV_INFO_FIELD_NAME, PV_DESCRIPTION_NAME, DESCRIPTION_LENGTH
from server_common.utilities import create_pv_name, remove_from_end, compress_and_hex
import json
from collections import OrderedDict

logger = logging.getLogger(__name__)

# PCASpy Enum PVs are limited to 14 items
AlarmStringsTruncated = [
    "NO_ALARM",
    "READ",
    "WRITE",
    "HIHI",
    "HIGH",
    "LOLO",
    "LOW",
    "STATE",
    "COS",
    "COMM",
    "TIMEOUT",
    "HWLIMIT",
    "CALC",
    "SCAN",
    "LINK",
    "OTHER",
    # "SOFT",
    # "BAD_SUB",
    # "UDF",
    # "DISABLE",
    # "SIMM",
    # "READ_ACCESS",
    # "WRITE_ACCESS"
]

PARAM_PREFIX = "PARAM"
BEAMLINE_PREFIX = "BL:"
SERVER_STATUS = "STAT"
SERVER_MESSAGE = "MSG"
SERVER_ERROR_LOG = "LOG"
BEAMLINE_MODE = BEAMLINE_PREFIX + "MODE"
BEAMLINE_MOVE = BEAMLINE_PREFIX + "MOVE"
REAPPLY_MODE_INITS = BEAMLINE_PREFIX + "INIT_ON_MOVE"

PARAM_INFO = "PARAM_INFO"
PARAM_INFO_COLLIMATION = "COLLIM_INFO"
PARAM_INFO_TOGGLE = "TOGGLE_INFO"
PARAM_INFO_SLITS = "SLIT_INFO"
PARAM_INFO_MISC = "MISC_INFO"
PARAM_INFO_FOOTPRINT = "FOOTPRINT_INFO"
DRIVER_INFO = "DRIVER_INFO"
BEAMLINE_CONSTANT_INFO = "CONST_INFO"
ALIGN_INFO = "ALIGN_INFO"
PARAM_INFO_LOOKUP = {BeamlineParameterGroup.ALL: PARAM_INFO,
                     BeamlineParameterGroup.COLLIMATION_PLANE: PARAM_INFO_COLLIMATION,
                     BeamlineParameterGroup.TOGGLE: PARAM_INFO_TOGGLE,
                     BeamlineParameterGroup.SLIT: PARAM_INFO_SLITS,
                     BeamlineParameterGroup.MISC: PARAM_INFO_MISC,
                     BeamlineParameterGroup.FOOTPRINT_PARAMETER: PARAM_INFO_FOOTPRINT,
                     }


IN_MODE_SUFFIX = ":IN_MODE"
SP_SUFFIX = ":SP"
SP_RBV_SUFFIX = ":SP:RBV"
ACTION_SUFFIX = ":ACTION"
SET_AND_NO_ACTION_SUFFIX = ":SP_NO_ACTION"
RBV_AT_SP = ":RBV:AT_SP"
CHANGING = ":CHANGING"
CHANGED_SUFFIX = ":CHANGED"
DEFINE_POS_SP = ":DEFINE_POS_SP"
DEFINE_POS_SET_AND_NO_ACTION = ":DEFINE_POS_SET_AND_NO_ACTION"
DEFINE_POS_ACTION = ":DEFINE_POS_ACTION"
DEFINE_POS_CHANGED = ":DEFINE_POS_CHANGED"
LOCKED = ":LOCKED"
LOCKED_SP = ":LOCKED_SP"

VAL_FIELD = ".VAL"
STAT_FIELD = ".STAT"
SEVR_FIELD = ".SEVR"
DESC_FIELD = ".DESC"
DISP_FIELD = ".DISP"
EGU_FIELD = ".EGU"

ALL_PARAM_SUFFIXES = [VAL_FIELD, STAT_FIELD, SEVR_FIELD, DISP_FIELD, EGU_FIELD, DESC_FIELD, SP_SUFFIX, SP_RBV_SUFFIX,
                      SET_AND_NO_ACTION_SUFFIX, CHANGED_SUFFIX, ACTION_SUFFIX, CHANGING, IN_MODE_SUFFIX, RBV_AT_SP, LOCKED, LOCKED_SP]

CONST_PREFIX = "CONST"

FOOTPRINT_PREFIX = "FP"
SAMPLE_LENGTH = "{}:{}".format(FOOTPRINT_PREFIX, "SAMPLE_LENGTH")
FP_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "FOOTPRINT")
DQQ_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "DQQ")
QMIN_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "QMIN")
QMAX_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "QMAX")
FOOTPRINT_PREFIXES = [FP_SP_KEY, FP_SP_RBV_KEY, FP_RBV_KEY]

MANAGER_FIELD = {"asg": "MANAGER"}
STANDARD_FLOAT_PV_FIELDS_WITH_MANAGER = STANDARD_FLOAT_PV_FIELDS | MANAGER_FIELD
PARAM_FIELDS_BINARY = {'type': 'enum', 'enums': ["NO", "YES"]}
PARAM_FIELDS_BINARY_WITH_MANAGER = PARAM_FIELDS_BINARY | MANAGER_FIELD
PARAM_IN_MODE = {'type': 'enum', 'enums': ["NO", "YES"]}
PARAM_FIELDS_ACTION = {'type': 'int', 'count': 1, 'value': 0}
PARAM_FIELDS_ACTION_WITH_MANAGER = PARAM_FIELDS_ACTION | MANAGER_FIELD
STANDARD_2048_CHAR_WF_FIELDS = {'type': 'char', 'count': 2048, 'value': ""}
STANDARD_STRING_FIELDS = {'type': 'string', 'value': ""}
STANDARD_DISP_FIELDS = {'type': 'enum', 'enums': ["0", "1"], 'value': 0}
ALARM_STAT_PV_FIELDS = {'type': 'enum', 'enums': AlarmStringsTruncated}
ALARM_SEVR_PV_FIELDS = {'type': 'enum', 'enums': SeverityStrings}


def is_pv_name_this_field(field_name, pv_name):
    """
    Args:
        field_name: field name to match
        pv_name: pv name to match

    Returns: True if field name is pv name (with oe without VAL field)

    """
    pv_name_no_val = remove_from_end(pv_name, VAL_FIELD)
    return pv_name_no_val == field_name

def check_if_pv_value_exceeds_max_size(value, max_size, pv):
    """
    Args:
        value: the pv value to set
        max_size: the maximum size of the pv
        pv: the pv

    Returns: The truncated value if maximum size is exceeded

    """
    if len(value) > max_size:
        STATUS_MANAGER.update_error_log(f"Size of {pv} exceeded limit of {max_size} and was truncated. "
                                         "Can you reduce the contents of the PV, if not increase the size of PV.")
        value = value[:max_size]
    return value

class PVManager:
    """
    Holds reflectometry PVs and associated utilities.
    """
    def __init__(self):
        """
        The constructor.
        """
        self._beamline = None  # type: Optional[ReflectometryServer.beamline.Beamline]
        self.PVDB = {}
        self.initial_PVs = []
        self._params_pv_lookup = OrderedDict()
        self._footprint_parameters = {}
        self._add_status_pvs()

        for pv_name in self.PVDB.keys():
            logger.info("Creating pv: {}".format(pv_name))

    def _add_status_pvs(self):
        """
        PVs for server status
        """
        status_fields = {'type': 'enum',
                         'enums': [code.display_string for code in STATUS.status_codes()],
                         'states': [code.alarm_severity for code in STATUS.status_codes()]}
        self._add_pv_with_fields(SERVER_STATUS, None, status_fields, "Status of the beam line", PvSort.RBV,
                                 archive=True, interest="HIGH", alarm=True, on_init=True)
        self._add_pv_with_fields(SERVER_MESSAGE, None, {'type': 'char', 'count': 400}, "Message about the beamline",
                                 PvSort.RBV, interest="HIGH", on_init=True)
        self._add_pv_with_fields(SERVER_ERROR_LOG, None, {'type': 'char', 'count': 10000},
                                 "Error log for the Reflectometry Server", PvSort.RBV, interest="HIGH",
                                 on_init=True)

    def set_beamline(self, beamline):
        """
        Set the beamline for the manager and add needed pvs

        Args:
            beamline (ReflectometryServer.beamline.Beamline): beamline to set

        """
        self._beamline = beamline

        self._add_global_pvs()
        self._add_footprint_calculator_pvs()
        self._add_all_parameter_pvs()
        self._add_all_driver_pvs()
        self._add_constants_pvs()

        for pv_name in [pv for pv in self.PVDB.keys() if pv not in self.initial_PVs]:
            logger.info("Creating pv: {}".format(pv_name))

    def _add_global_pvs(self):
        """
        Add PVs that affect the whole of the reflectometry system to the server's PV database.

        """
        self._add_pv_with_fields(BEAMLINE_MOVE, None, PARAM_FIELDS_ACTION, "Move the beam line", PvSort.RBV,
                                 archive=True, interest="HIGH")
        # PVs for mode
        mode_fields = {'type': 'enum', 'enums': self._beamline.mode_names}
        self._add_pv_with_fields(BEAMLINE_MODE, None, mode_fields, "Beamline mode", PvSort.RBV, archive=True,
                                 interest="HIGH")
        self._add_pv_with_fields(BEAMLINE_MODE + SP_SUFFIX, None, mode_fields, "Beamline mode", PvSort.SP)

        self._add_pv_with_fields(REAPPLY_MODE_INITS, None, PARAM_FIELDS_BINARY, "Apply mode inits on move all",
                                 PvSort.RBV, archive=True, interest="MEDIUM")

    def _add_footprint_calculator_pvs(self):
        """
        Add PVs related to the footprint calculation to the server's PV database.
        """
        self._add_pv_with_fields(SAMPLE_LENGTH, None, STANDARD_FLOAT_PV_FIELDS,
                                 "Sample Length", PvSort.SP_RBV, archive=True, interest="HIGH")

        for prefix in FOOTPRINT_PREFIXES:
            for template, description in [(FP_TEMPLATE, "Beam Footprint"),
                                          (DQQ_TEMPLATE, "Beam Resolution dQ/Q"),
                                          (QMIN_TEMPLATE, "Minimum measurable Q with current setup"),
                                          (QMAX_TEMPLATE, "Maximum measurable Q with current setup")]:
                self._add_pv_with_fields(template.format(prefix), None,
                                         STANDARD_FLOAT_PV_FIELDS,
                                         description, PvSort.RBV, archive=True, interest="HIGH")

    def _add_all_parameter_pvs(self):
        """
        Add PVs for each beamline parameter in the reflectometry configuration to the server's PV database.
        """
        param_info = {}
        for group in BeamlineParameterGroup:
            param_info[group] = []
        align_info = []
        for parameter in self._beamline.parameters.values():
            try:
                param_info_record = self._add_parameter_pvs(parameter)
                if param_info_record is not None:
                    for group in parameter.group_names:
                        param_info[group].append(param_info_record)
                    if parameter.define_current_value_as is not None:
                        align_info_record = {
                            "name": param_info_record["name"],
                            "prepended_alias": param_info_record["prepended_alias"],
                            "type": "align",
                            "description": ""
                        }
                        align_info.append(align_info_record)

            except Exception as err:
                STATUS_MANAGER.update_error_log("Error adding PV for parameter {}: {}".format(parameter.name, err), err)
                STATUS_MANAGER.update_active_problems(
                    ProblemInfo("Error adding parameter PV", parameter.name, Severity.MAJOR_ALARM))

        for param_group in BeamlineParameterGroup:
            value = compress_and_hex(json.dumps(param_info[param_group]))
            value = check_if_pv_value_exceeds_max_size(value, STANDARD_2048_CHAR_WF_FIELDS["count"], param_group)

            self._add_pv_with_fields(PARAM_INFO_LOOKUP[param_group], None, STANDARD_2048_CHAR_WF_FIELDS,
                                     BeamlineParameterGroup.description(param_group), None, value=value)

        value = compress_and_hex(json.dumps(align_info))
        value = check_if_pv_value_exceeds_max_size(value, STANDARD_2048_CHAR_WF_FIELDS["count"], ALIGN_INFO)
        self._add_pv_with_fields(ALIGN_INFO, None, STANDARD_2048_CHAR_WF_FIELDS, "All alignment pvs information",
                                 None, value=value)

    def _add_parameter_pvs(self, parameter):
        """
        Adds all PVs needed for one beamline parameter to the PV database.

        Args:
            parameter (ReflectometryServer.parameters.BeamlineParameter): the beamline parameter

        Returns:
            parameter information
        """
        param_name = parameter.name
        description = parameter.description
        param_alias = create_pv_name(param_name, list(self.PVDB.keys()), PARAM_PREFIX, limit=10)
        prepended_alias = "{}:{}".format(PARAM_PREFIX, param_alias)

        parameter_type = parameter.parameter_type
        fields = PARAMS_FIELDS_BEAMLINE_TYPES[parameter_type].copy()
        fields["unit"] = parameter.engineering_unit
        if parameter_type == BeamlineParameterType.ENUM:
            fields["enums"] = parameter.options

        # Readback PV
        self._add_pv_with_fields(prepended_alias, param_name, fields, description, PvSort.RBV, archive=True,
                                 interest="HIGH")

        # Setpoint PV
        self._add_pv_with_fields(prepended_alias + SP_SUFFIX, param_name, fields, description, PvSort.SP,
                                 archive=True)

        # Setpoint readback PV
        self._add_pv_with_fields(prepended_alias + SP_RBV_SUFFIX, param_name, fields, description, PvSort.SP_RBV)

        # Set value and do not action PV
        self._add_pv_with_fields(prepended_alias + SET_AND_NO_ACTION_SUFFIX, param_name, fields, description,
                                 PvSort.SET_AND_NO_ACTION, is_disabled_on_init=parameter.sp_mirrors_rbv)

        # Changed PV
        self._add_pv_with_fields(prepended_alias + CHANGED_SUFFIX, param_name, PARAM_FIELDS_BINARY, description,
                                 PvSort.CHANGED)

        # Action PV
        self._add_pv_with_fields(prepended_alias + ACTION_SUFFIX, param_name, PARAM_FIELDS_ACTION, description,
                                 PvSort.ACTION)

        # Moving state PV
        self._add_pv_with_fields(prepended_alias + CHANGING, param_name, PARAM_FIELDS_BINARY, description,
                                 PvSort.CHANGING)

        # In mode PV
        self._add_pv_with_fields(prepended_alias + IN_MODE_SUFFIX, param_name, PARAM_IN_MODE, description,
                                 PvSort.IN_MODE)

        # RBV to SP:RBV tolerance
        self._add_pv_with_fields(prepended_alias + RBV_AT_SP, param_name, PARAM_FIELDS_BINARY, description,
                                 PvSort.RBV_AT_SP)

        # Locked PV
        self._add_pv_with_fields(prepended_alias + LOCKED, param_name, PARAM_FIELDS_BINARY_WITH_MANAGER, description,
                                 PvSort.LOCKED)

        # Locked setpoint PV
        self._add_pv_with_fields(prepended_alias + LOCKED_SP, param_name, PARAM_FIELDS_BINARY_WITH_MANAGER, description,
                                 PvSort.LOCKED_SP)

        # define position at
        if parameter.define_current_value_as is not None:
            self._add_pv_with_fields(prepended_alias + DEFINE_POS_SP, param_name, STANDARD_FLOAT_PV_FIELDS_WITH_MANAGER, description,
                                     PvSort.DEFINE_POS_SP)

            self._add_pv_with_fields(prepended_alias + DEFINE_POS_SET_AND_NO_ACTION, param_name, STANDARD_FLOAT_PV_FIELDS_WITH_MANAGER, description,
                                     PvSort.DEFINE_POS_SET_AND_NO_ACTION)

            self._add_pv_with_fields(prepended_alias + DEFINE_POS_ACTION, param_name, PARAM_FIELDS_ACTION_WITH_MANAGER, description,
                                     PvSort.DEFINE_POS_ACTION)

            self._add_pv_with_fields(prepended_alias + DEFINE_POS_CHANGED, param_name, PARAM_FIELDS_BINARY_WITH_MANAGER, description,
                                     PvSort.DEFINE_POS_CHANGED)

        # Engineering Unit
        egu_fields = STANDARD_STRING_FIELDS.copy()
        egu_fields["value"] = parameter.engineering_unit
        self.PVDB[prepended_alias + EGU_FIELD] = egu_fields

        return {"name": param_name,
                "prepended_alias": prepended_alias,
                "type": BeamlineParameterType.name_for_param_list(parameter_type),
                "characteristic_value": parameter.characteristic_value,
                "description": parameter.description}

    def _add_pv_with_fields(self, pv_name, param_name, pv_fields, description, sort, archive=False, interest=None,
                            alarm=False, value=None, on_init=False, is_disabled_on_init=False):
        """
        Add param to pv list with .val and correct fields and to parm look up
        Args:
            pv_name: name of the pv
            param_name: name of the parameter; None for not a parameter
            pv_fields: pv fields to use
            description: description of the pv for .DESC field
            sort: sort of pv it is
            archive: True if it should be archived
            interest: level of interest; None is not interesting
            alarm: True if this pv represents the alarm state of the IOC; false otherwise
            on_init: True if this PV is added at the start of server initialisation
            is_disabled_on_init: True to disable on init; False otherwise. This is used when the disabled value is
                static for the lifetime of the PV (e.g. when sp mirrors rbv) otherwise a listener should be used

        Returns:

        """
        pv_fields = pv_fields.copy()
        description_for_pv = description
        if sort is not None:
            description_for_pv = description + PvSort.what(sort)
        pv_fields[PV_DESCRIPTION_NAME] = description_for_pv[0:DESCRIPTION_LENGTH]

        if value is not None:
            pv_fields["value"] = value

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
        self.PVDB[pv_name + DESC_FIELD] = {'type': 'string', 'value': pv_fields[PV_DESCRIPTION_NAME]}
        self.PVDB[pv_name + STAT_FIELD] = ALARM_STAT_PV_FIELDS.copy()
        self.PVDB[pv_name + SEVR_FIELD] = ALARM_SEVR_PV_FIELDS.copy()
        self.PVDB[pv_name + DISP_FIELD] = STANDARD_DISP_FIELDS.copy()
        if is_disabled_on_init:
            self.PVDB[pv_name + DISP_FIELD]["value"] = 1

        if param_name is not None:
            self._params_pv_lookup[pv_name] = (param_name, sort)

        if on_init:
            self.initial_PVs.append(pv_name)
            self.initial_PVs.append(pv_name + VAL_FIELD)
            self.initial_PVs.append(pv_name + STAT_FIELD)
            self.initial_PVs.append(pv_name + SEVR_FIELD)
            self.initial_PVs.append(pv_name + DISP_FIELD)

    def get_init_filtered_pvdb(self):
        """

        Returns:
            pvs that were created after beamline was set.

        """
        return {key: value for key, value in self.PVDB.items() if key not in self.initial_PVs}

    def _add_all_driver_pvs(self):
        """
        Add all pvs for the drivers.
        """
        self.drivers_pv = {}
        driver_info = []
        for driver in self._beamline.drivers:
            if driver.has_engineering_correction:
                correction_alias = create_pv_name(driver.name, list(self.PVDB.keys()), "COR", limit=12,
                                                  allow_colon=True)
                prepended_alias = "{}:{}".format("COR", correction_alias)

                self._add_pv_with_fields(prepended_alias, None, STANDARD_FLOAT_PV_FIELDS, "Engineering Correction",
                                         None, archive=True)
                self._add_pv_with_fields("{}:DESC".format(prepended_alias), None, STANDARD_2048_CHAR_WF_FIELDS,
                                         "Engineering Correction Full Description", None)

                self.drivers_pv[driver] = prepended_alias

                driver_info.append({"name": driver.name, "prepended_alias": prepended_alias})

        value = compress_and_hex(json.dumps(driver_info))
        value = check_if_pv_value_exceeds_max_size(value, STANDARD_2048_CHAR_WF_FIELDS["count"], DRIVER_INFO)
        self._add_pv_with_fields(DRIVER_INFO, None, STANDARD_2048_CHAR_WF_FIELDS, "All corrections information",
                                 None, value=value)

    def _add_constants_pvs(self):
        """
        Add pvs for the beamline constants
        """

        beamline_constant_info = []

        for beamline_constant in self._beamline.beamline_constants:
            try:
                const_alias = create_pv_name(beamline_constant.name, list(self.PVDB.keys()), CONST_PREFIX,
                                             limit=20, allow_colon=True)
                prepended_alias = "{}:{}".format(CONST_PREFIX, const_alias)

                if isinstance(beamline_constant.value, bool):
                    value = 1 if bool(beamline_constant.value) else 0
                    fields = PARAM_FIELDS_BINARY
                elif isinstance(beamline_constant.value, str):
                    value = beamline_constant.value
                    fields = STANDARD_2048_CHAR_WF_FIELDS
                else:
                    value = float(beamline_constant.value)
                    fields = STANDARD_FLOAT_PV_FIELDS

                self._add_pv_with_fields(prepended_alias, None, fields, beamline_constant.description, None,
                                         interest="MEDIUM", value=value)
                logger.info("Adding Constant {} with value {}".format(beamline_constant.name, beamline_constant.value))
                beamline_constant_info.append(
                    {"name": beamline_constant.name,
                     "prepended_alias": prepended_alias,
                     "type": "float_value",
                     "description": beamline_constant.description})
            except Exception as err:
                STATUS_MANAGER.update_error_log("Error adding constant {}: {}".format(beamline_constant.name, err), err)
                STATUS_MANAGER.update_active_problems(
                    ProblemInfo("Error adding PV for beamline constant", beamline_constant.name, Severity.MAJOR_ALARM))

        value = compress_and_hex(json.dumps(beamline_constant_info))
        value = check_if_pv_value_exceeds_max_size(value, STANDARD_2048_CHAR_WF_FIELDS["count"], BEAMLINE_CONSTANT_INFO)
        self._add_pv_with_fields(BEAMLINE_CONSTANT_INFO, None, STANDARD_2048_CHAR_WF_FIELDS, "All value parameters",
                                 None, value=value)

    def param_names_pv_names_and_sort(self):
        """

        Returns:
            (list[str, tuple[str, PvSort]]): The list of PVs of all beamline parameters.

        """
        return list(self._params_pv_lookup.items())

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
        return self._params_pv_lookup[self.strip_fields_from_pv(pv_name)]

    def _get_base_param_pv(self, pv_name):
        """
        Args:
            pv_name: name of pv for which to get the base pv

        Returns:
            (str): base parameter pv stripped of any fields / suffixes
        """
        for field in ALL_PARAM_SUFFIXES:
            pv_name = remove_from_end(pv_name, field)
        return pv_name

    def get_all_pvs_for_param(self, pv_name):
        """
        Get a list of all suffixed PVs for a given parameter.

        Args:
            pv_name: name of pv for which to get the list of PVs

        Returns:
            (list[str]): The list of all PVs related to this parameter
        """
        base_pv = self._get_base_param_pv(pv_name)
        all_pvs = [base_pv] + [(base_pv + suffix) for suffix in ALL_PARAM_SUFFIXES]
        return all_pvs

    def strip_fields_from_pv(self, pv_name):
        """
        Remove suffixes for fields from the end of a given PV.

        Args:
            pv_name: name of the pv

        Returns: The PV name with any of the known field suffixes stripped off the end.
        """
        for field in [VAL_FIELD, STAT_FIELD, SEVR_FIELD, DISP_FIELD]:
            pv_name = remove_from_end(pv_name, field)
        return pv_name

    @staticmethod
    def is_beamline_mode(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the beamline mode pv
        """
        pv_name_no_val = remove_from_end(pv_name, VAL_FIELD)
        return pv_name_no_val == BEAMLINE_MODE or pv_name_no_val == BEAMLINE_MODE + SP_SUFFIX

    @staticmethod
    def is_alarm_status(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this is an alarm status pv
        """
        return pv_name.endswith(STAT_FIELD)

    @staticmethod
    def is_alarm_severity(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this is an alarm severity pv
        """
        return pv_name.endswith(SEVR_FIELD)

    @staticmethod
    def is_disable_field(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this is an alarm severity pv
        """
        return pv_name.endswith(DISP_FIELD)
