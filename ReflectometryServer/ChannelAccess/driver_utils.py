from enum import Enum
from typing import Tuple, Union, Dict

from ReflectometryServer import Beamline
from ReflectometryServer.ChannelAccess.constants import STANDARD_FLOAT_PV_FIELDS, MAX_ALARM_ID

from ReflectometryServer.parameters import BeamlineParameterType, ParameterUpdateBase
from ReflectometryServer.server_status_manager import STATUS_MANAGER
from server_common.utilities import print_and_log, SEVERITY
from server_common.channel_access import AlarmSeverity, AlarmStatus

# field for in beam parameter
OUT_IN_ENUM_TEXT = ["OUT", "IN"]


# Field for the various type of beamline parameter
PARAMS_FIELDS_BEAMLINE_TYPES = {
    BeamlineParameterType.IN_OUT: {'type': 'enum', 'enums': OUT_IN_ENUM_TEXT},
    BeamlineParameterType.FLOAT: STANDARD_FLOAT_PV_FIELDS,
    BeamlineParameterType.ENUM: {'type': 'enum', 'enums': []}}


def convert_from_epics_pv_value(parameter_type, value, pv_fields):
    """
    Convert from epic pv value to the parameter value
    Args:
        parameter_type (BeamlineParameterType): parameters type
        value: value to convert
        pv_fields: fields on the pv

    Returns: epics value

    """
    if parameter_type == BeamlineParameterType.IN_OUT:
        return value == OUT_IN_ENUM_TEXT.index("IN")
    elif parameter_type == BeamlineParameterType.ENUM:
        return pv_fields["enums"][value]
    else:
        return value


def _convert_to_epics_pv_value(parameter_type: BeamlineParameterType, value: Union[float, int, str, bool],
                               alarm_severity: AlarmSeverity, alarm_status: AlarmStatus, pv_fields: Dict):
    """
    Convert from parameter value to the epic pv value
    Args:
        parameter_type: parameters type
        value: value to convert
        alarm_severity: alarm severity
        alarm_status: alarm status
        pv_fields: pv fields for the pv, e.g. used for options on en enum field

    Returns: epics value and alarms

    """
    if alarm_status is None:
        status = alarm_status
    else:
        status = min(MAX_ALARM_ID, alarm_status)
    severity = alarm_severity
    if parameter_type == BeamlineParameterType.IN_OUT:
        if value:
            pv_value = OUT_IN_ENUM_TEXT.index("IN")
        else:
            pv_value = OUT_IN_ENUM_TEXT.index("OUT")
    elif parameter_type == BeamlineParameterType.ENUM:
        try:
            pv_value = pv_fields.get("enums", None).index(value)
        except ValueError:
            pv_value = -1
            status = AlarmStatus.State
            severity = AlarmSeverity.Invalid
            STATUS_MANAGER.update_error_log("Value set of parameter which is not in pv options {}".format(value))
    else:
        if value is None:
            pv_value = float("NaN")
        else:
            pv_value = value
    return pv_value, severity, status


class PvSort(Enum):
    """
    Enum for the type of PV
    """
    RBV = 0
    ACTION = 1
    SP_RBV = 2
    SP = 3
    SET_AND_NO_ACTION = 4
    CHANGED = 6
    IN_MODE = 7
    CHANGING = 8
    RBV_AT_SP = 9
    DEFINE_POS_AS = 10

    @staticmethod
    def what(pv_sort):
        """
        Args:
            pv_sort: pv sort to determine

        Returns: what the pv sort does
        """
        if pv_sort == PvSort.RBV:
            return ""
        elif pv_sort == PvSort.ACTION:
            return "(Do the action)"
        elif pv_sort == PvSort.SP_RBV:
            return "(Set point readback)"
        elif pv_sort == PvSort.SP:
            return "(Set point)"
        elif pv_sort == PvSort.SET_AND_NO_ACTION:
            return "(Set point with no action executed)"
        elif pv_sort == PvSort.CHANGED:
            return "(Is changed)"
        elif pv_sort == PvSort.IN_MODE:
            return "(Is in mode)"
        elif pv_sort == PvSort.CHANGING:
            return "(Is changing)"
        elif pv_sort == PvSort.RBV_AT_SP:
            return "(Tolerance between RBV and target set point)"
        elif pv_sort == PvSort.DEFINE_POS_AS:
            return "(Define the value of current position)"
        else:
            print_and_log("Unknown pv sort!! {}".format(pv_sort), severity=SEVERITY.MAJOR, src="REFL")
            return "(unknown)"

    def get_from_parameter(self, parameter, pv_fields):
        """
        Get the value of the correct sort from a parameter
        Args:
            parameter(ReflectometryServer.parameters.BeamlineParameter): the parameter to get the value from
            pv_fields: values that the pv can take if

        Returns: the value of the parameter of the correct sort and their alarms
        """
        severity = AlarmSeverity.No
        status = AlarmStatus.No
        if self == PvSort.SP:
            value, severity, status = _convert_to_epics_pv_value(parameter.parameter_type, parameter.sp,
                                                                 AlarmSeverity.No, AlarmStatus.No, pv_fields)
        elif self == PvSort.SP_RBV:
            value, severity, status = _convert_to_epics_pv_value(parameter.parameter_type, parameter.sp_rbv,
                                                                 AlarmSeverity.No, AlarmStatus.No, pv_fields)
        elif self == PvSort.RBV:
            value, severity, status = _convert_to_epics_pv_value(parameter.parameter_type, parameter.rbv,
                                                                 parameter.alarm_severity, parameter.alarm_status,
                                                                 pv_fields)
        elif self == PvSort.SET_AND_NO_ACTION:
            value, severity, status = _convert_to_epics_pv_value(parameter.parameter_type, parameter.sp_no_move,
                                                                 AlarmSeverity.No, AlarmStatus.No, pv_fields)
        elif self == PvSort.CHANGED:
            value = parameter.sp_changed
        elif self == PvSort.ACTION:
            value = parameter.move
        elif self == PvSort.CHANGING:
            value = parameter.is_changing
        elif self == PvSort.RBV_AT_SP:
            value = parameter.rbv_at_sp
        elif self == PvSort.DEFINE_POS_AS:
            if parameter.define_current_value_as is None:
                value, severity, status = float("NaN"), AlarmSeverity.Invalid, AlarmStatus.UDF
            else:
                value = parameter.define_current_value_as.new_value
        else:
            value, severity, status = float("NaN"), AlarmSeverity.Invalid, AlarmStatus.UDF
            STATUS_MANAGER.update_error_log("PVSort not understood {}".format(PvSort))

        return value, severity, status


class DriverParamHelper:
    """
    Driver to help with channel access to parameters
    """

    def __init__(self, pv_manager, beamline: Beamline):
        """
        Initialise.
        Args:
            pv_manager: pv manger
            beamline: the beamline to use this with
        """
        self._pv_manager = pv_manager
        self._beamline = beamline

    def param_write(self, pv_name, value):
        """
        Write a parameter value from epics to the beamline.
        Args:
            pv_name: pv name
            value: value to set

        Returns:
            True if value was accepted by the system; False otherwise

        """
        value_accepted = True
        param_name, param_sort = self._pv_manager.get_param_name_and_sort_from_pv(pv_name)
        param = self._beamline.parameter(param_name)
        if param_sort == PvSort.ACTION:
            param.move = 1
        elif param_sort == PvSort.SP:
            param.sp = convert_from_epics_pv_value(param.parameter_type, value, self._pv_manager.PVDB[pv_name])
        elif param_sort == PvSort.SET_AND_NO_ACTION:
            param.sp_no_move = convert_from_epics_pv_value(param.parameter_type, value, self._pv_manager.PVDB[pv_name])
        elif param_sort == PvSort.DEFINE_POS_AS:
            param.define_current_value_as.new_value = convert_from_epics_pv_value(param.parameter_type, value,
                                                                                  self._pv_manager.PVDB[pv_name])
        else:
            STATUS_MANAGER.update_error_log("Error: PV {} is read only".format(pv_name))
            value_accepted = False
        return value_accepted

    def get_param_monitor_updates(self) -> Tuple[str, Union[float, int, str, bool], AlarmSeverity, AlarmStatus]:
        """
        This is a generator over the names and values (with alarms) of the parameters
        Returns: tuple of
            pv name
            pv value
            alarm severity
            alarm status
        """
        for pv_name, (param_name, param_sort) in self._pv_manager.param_names_pv_names_and_sort():
            parameter = self._beamline.parameter(param_name)
            if param_sort not in [PvSort.IN_MODE, PvSort.CHANGING]:
                pv_fields = self._pv_manager.PVDB[pv_name]
                value, alarm_severity, alarm_status = param_sort.get_from_parameter(parameter, pv_fields)
                yield pv_name, value, alarm_severity, alarm_status

    def get_param_update_from_event(self, pv_name: str, param_type: BeamlineParameterType, update: ParameterUpdateBase)\
            -> Tuple[str, Union[float, int, str, bool], AlarmSeverity, AlarmStatus]:
        """
        Given an update event get the update information for updating a pv field
        Args:
            pv_name: name of the pv
            param_type: parameter type
            update: update event

        Returns:
            name of the pv
            value
            alarm severity
            alarm status

        """
        pv_fields = self._pv_manager.PVDB[pv_name]
        value, severity, status = _convert_to_epics_pv_value(param_type, update.value, update.alarm_severity,
                                                             update.alarm_status, pv_fields)
        return pv_name, value, severity, status
