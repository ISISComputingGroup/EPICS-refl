"""
Driver for the reflectometry server.
"""
import logging
from functools import partial

from pcaspy import Driver, Alarm, Severity
from pcaspy.driver import manager, Data

from ReflectometryServer import Beamline
from ReflectometryServer.ChannelAccess.constants import REFLECTOMETRY_PREFIX
from ReflectometryServer.ChannelAccess.driver_utils import DriverParamHelper
from ReflectometryServer.ChannelAccess.pv_manager import PvSort, BEAMLINE_MODE, VAL_FIELD, SERVER_STATUS, \
    SERVER_MESSAGE, SP_SUFFIX, FP_TEMPLATE, DQQ_TEMPLATE, QMIN_TEMPLATE, QMAX_TEMPLATE, \
    IN_MODE_SUFFIX, SERVER_ERROR_LOG
from ReflectometryServer.server_status_manager import STATUS_MANAGER, StatusUpdate, ProblemInfo, ErrorLogUpdate
from ReflectometryServer.footprint_manager import FootprintSort
from ReflectometryServer.engineering_corrections import CorrectionUpdate
from ReflectometryServer.parameters import BeamlineParameterGroup, ParameterReadbackUpdate, \
    ParameterSetpointReadbackUpdate, ParameterAtSetpointUpdate, ParameterChangingUpdate, ParameterInitUpdate, \
    ParameterUpdateBase, BeamlineParameterType
from server_common.loggers.isis_logger import IsisPutLog

logger = logging.getLogger(__name__)


class ReflectometryDriver(Driver):
    """
    The driver which provides an interface for the reflectometry server to channel access by creating PVs and processing
    incoming CA get and put requests.
    """
    _beamline: Beamline

    def __init__(self, server, pv_manager):
        """
        The Constructor.
        Args:
            server: The PCASpy server.
            pv_manager(ReflectometryServer.ChannelAccess.pv_manager.PVManager): The manager mapping PVs to objects in
                the beamline.
        """
        super(ReflectometryDriver, self).__init__()
        self._ca_server = server
        self._initialised = False
        self._beamline = None
        self._pv_manager = pv_manager
        self._footprint_manager = None

        self.add_trigger_status_change_listener()
        self.add_trigger_log_update_listener()
        self.put_log = IsisPutLog("REFL")
        self._driver_help = None

    def set_beamline(self, beamline):
        """
        Set the beamline model to which the reflectometry server should provide an interface.

        Args:
            beamline(ReflectometryServer.beamline.Beamline): The beamline configuration.
        """

        self._beamline = beamline
        self._driver_help = DriverParamHelper(self._pv_manager, beamline)
        self._footprint_manager = beamline.footprint_manager

        for reason, pv in list(manager.pvs[self.port].items()):
            if reason not in self._pv_manager.initial_PVs:
                data = Data()
                data.value = pv.info.value
                self.pvDB[reason] = data

        for reason in list(self._pv_manager.PVDB.keys()):
            self.setParamStatus(reason, severity=Severity.NO_ALARM, alarm=Alarm.NO_ALARM)

        self.add_param_listeners()
        self.add_trigger_active_mode_change_listener()
        self.add_footprint_param_listeners()
        self._add_trigger_on_engineering_correction_change()

        self.update_monitors()
        self._initialised = True

    def read(self, reason):
        """
        Processes an incoming caget request.

        Args:
            reason (str): The PV that is being read.

        Returns: The value associated to this PV
        """
        try:
            if self._initialised:
                if self._pv_manager.is_param(reason):
                    return self.getParam(reason)

                elif self._pv_manager.is_beamline_mode(reason):
                    return self._beamline_mode_value(self._beamline.active_mode)

                elif self._pv_manager.is_beamline_move(reason):
                    return self._beamline.move

                elif self._pv_manager.is_server_status(reason):
                    beamline_status_enums = self._pv_manager.PVDB[SERVER_STATUS]["enums"]
                    new_value = beamline_status_enums.index(STATUS_MANAGER.status.display_string)
                    #  Set the value so that the error condition is set
                    self.setParam(reason, new_value)
                    return new_value

                elif self._pv_manager.is_server_message(reason):
                    return STATUS_MANAGER.message
                elif self._pv_manager.is_error_log(reason):
                    return STATUS_MANAGER.error_log
                elif self._pv_manager.is_sample_length(reason):
                    return self._footprint_manager.get_sample_length()
                elif self._pv_manager.is_alarm_status(reason):
                    return self.getParamDB(self._pv_manager.strip_fields_from_pv(reason)).alarm
                elif self._pv_manager.is_alarm_severity(reason):
                    return self.getParamDB(self._pv_manager.strip_fields_from_pv(reason)).severity
        except Exception as e:
            STATUS_MANAGER.update_error_log("Exception when reading parameter {}".format(reason), e)
            STATUS_MANAGER.update_active_problems(
                ProblemInfo("PV Value read caused exception.", reason, Severity.MAJOR_ALARM))
            return

        return self.getParam(reason)

    def _beamline_mode_value(self, mode):
        beamline_mode_enums = self._pv_manager.PVDB[BEAMLINE_MODE]["enums"]
        return beamline_mode_enums.index(mode)

    def write(self, reason, value):
        """
        Process an incoming caput request.
        :param reason: The PV that is being written to.
        :param value: The value being written to the PV
        """
        value_accepted = True
        try:
            if self._pv_manager.is_param(reason):
                value_accepted = self._driver_help.param_write(reason, value)
            elif self._pv_manager.is_beamline_move(reason):
                self._beamline.move = 1
            elif self._pv_manager.is_beamline_mode(reason):
                try:
                    beamline_mode_enums = self._pv_manager.PVDB[BEAMLINE_MODE]["enums"]
                    new_mode_name = beamline_mode_enums[value]
                    self._beamline.active_mode = new_mode_name
                    self._on_bl_mode_change(new_mode_name, self._beamline.get_param_names_in_mode())
                except ValueError:
                    STATUS_MANAGER.update_error_log("Invalid value entered for mode. (Possible modes: {})".format(
                        ",".join(self._beamline.mode_names)))
                    value_accepted = False
            elif self._pv_manager.is_sample_length(reason):
                self._footprint_manager.set_sample_length(value)
            else:
                STATUS_MANAGER.update_error_log("Error: PV is read only")
                value_accepted = False

            if value_accepted:
                pv_name = "{}{}".format(REFLECTOMETRY_PREFIX, reason)
                self.put_log.write_pv_put(pv_name, value, self.getParam(reason))
                self._update_param_both_pv_and_pv_val(reason, value)
                self.update_monitors()
        except Exception as e:
            STATUS_MANAGER.update_error_log("PV Value {} rejected by server for {}.".format(value, reason), e)
            STATUS_MANAGER.update_active_problems(ProblemInfo("PV Value rejected by server.", reason,
                                                              Severity.MINOR_ALARM))
            value_accepted = False
        return value_accepted

    def update_monitors(self):
        """
        Updates the PV values and alarms for each parameter so that changes are visible to monitors.
        """
        # with self.monitor_lock:
        for pv_name, value, alarm_severity, alarm_status in self._driver_help.get_param_monitor_updates():
            self._update_param_both_pv_and_pv_val(pv_name, value, alarm_severity, alarm_status)

        self._update_all_footprints()
        self.updatePVs()

    def _update_all_footprints(self):
        """
        Updates footprint calculations for all value sorts.
        """
        self._update_footprint(FootprintSort.SP, 1)
        self._update_footprint(FootprintSort.SP_RBV, 1)
        self._update_footprint(FootprintSort.RBV, 1)

    def _update_footprint(self, sort, _):
        """
        Updates footprint PVs for a given sort of value.

        Args:
            sort{ReflectometryServer.pv_manager.FootprintSort): The sort of value for which to update the footprint PVs
        """
        prefix = FootprintSort.prefix(sort)
        self._update_param_both_pv_and_pv_val(FP_TEMPLATE.format(prefix), self._footprint_manager.get_footprint(sort))
        self._update_param_both_pv_and_pv_val(DQQ_TEMPLATE.format(prefix), self._footprint_manager.get_resolution(sort))
        self._update_param_both_pv_and_pv_val(QMIN_TEMPLATE.format(prefix), self._footprint_manager.get_q_min(sort))
        self._update_param_both_pv_and_pv_val(QMAX_TEMPLATE.format(prefix), self._footprint_manager.get_q_max(sort))
        self.updatePVs()

    def _update_param_both_pv_and_pv_val(self, pv_name, value, alarm_severity=None,  alarm_status=None):
        """
        Update a parameter value (both base and .VAL) and its alarms.

        Args:
            pv_name: name of the pv
            value: value of the parameter
            alarm_severity: current alarm severity of the parameter
            alarm_status: current alarm status of the parameter
        """
        if value is None:
            raise ValueError("PV cannot be set to None. pv_name '{}'".format(pv_name))
        self.setParam(pv_name, value)
        self.setParam(pv_name + VAL_FIELD, value)
        self.setParamStatus(pv_name, alarm_status, alarm_severity)

    def _update_param_listener(self, pv_name: str, param_type: BeamlineParameterType, update: ParameterUpdateBase):
        """
        Listener for responding to updates from the command line parameter
        Args:
            pv_name: name of the pv
            update (NamedTuple): update from this parameter, expected to have at least a "value" attribute.
        """
        pv_name, value, alarm_severity, alarm_status = \
            self._driver_help.get_param_update_from_event(pv_name, update, param_type)
        self._update_param_both_pv_and_pv_val(pv_name, value, alarm_severity, alarm_status)
        self.updatePVs()

    def add_param_listeners(self):
        """
        Add listeners to beamline parameter changes, which update pvs in the server
        """
        for pv_name, (param_name, param_sort) in self._pv_manager.param_names_pv_names_and_sort():
            parameter = self._beamline.parameter(param_name)
            parameter.add_listener(ParameterInitUpdate, partial(self._update_param_listener, pv_name, parameter.parameter_type))
            if param_sort == PvSort.RBV:
                parameter.add_listener(ParameterReadbackUpdate, partial(self._update_param_listener, pv_name, parameter.parameter_type))
            if param_sort == PvSort.SP_RBV:
                parameter.add_listener(ParameterSetpointReadbackUpdate, partial(self._update_param_listener, pv_name, parameter.parameter_type))
            if param_sort == PvSort.CHANGING:
                parameter.add_listener(ParameterChangingUpdate, partial(self._update_binary_listener, pv_name))
            if param_sort == PvSort.RBV_AT_SP:
                parameter.add_listener(ParameterAtSetpointUpdate, partial(self._update_binary_listener, pv_name))

    def _update_binary_listener(self, pv_name, update):
        self.setParam(pv_name, update.value)
        self.updatePVs()

    def _on_bl_mode_change(self, mode, params_in_mode):
        """
        Beamline mode change in driver
        Args:
            mode (str): to change to
            params_in_mode : list of parameters in the mode given
        """

        for pv_name, (param_name, param_sort) in self._pv_manager.param_names_pv_names_and_sort():
            if param_sort is PvSort.RBV:
                if param_name in params_in_mode:
                    self._update_param_both_pv_and_pv_val(pv_name + IN_MODE_SUFFIX, 1)
                else: 
                    self._update_param_both_pv_and_pv_val(pv_name + IN_MODE_SUFFIX, 0)
     
        mode_value = self._beamline_mode_value(mode)
        self._update_param_both_pv_and_pv_val(BEAMLINE_MODE, mode_value)
        self._update_param_both_pv_and_pv_val(BEAMLINE_MODE + SP_SUFFIX, mode_value)
        self.updatePVs()

    def _on_server_status_change(self, update):
        """
        Update the overall status of the beamline.

        Args:
            update (ReflectometryServer.server_status_manager.StatusUpdate): The new server status and message.
        """
        beamline_status_enums = self._pv_manager.PVDB[SERVER_STATUS]["enums"]
        status_id = beamline_status_enums.index(update.server_status.display_string)
        self._update_param_both_pv_and_pv_val(SERVER_STATUS, status_id)
        self._update_param_both_pv_and_pv_val(SERVER_MESSAGE, update.server_message)
        self.updatePVs()

    def _on_error_log_update(self, update):
        """
        Update the overall status of the beamline.

        Args:
            update (ReflectometryServer.server_status_manager.StatusUpdate): The new server status and message.
        """
        self._update_param_both_pv_and_pv_val(SERVER_ERROR_LOG, update.log_as_string)
        self.updatePVs()

    def add_trigger_active_mode_change_listener(self):
        """
        Adds the monitor on the active mode, if this changes a monitor update is posted.
        """
        self._beamline.add_active_mode_change_listener(self._on_bl_mode_change)
        self._on_bl_mode_change(self._beamline.active_mode, self._beamline.get_param_names_in_mode())

    def add_trigger_status_change_listener(self):
        """
        Adds the monitor on the beamline status, if this changes a monitor update is posted.
        """
        STATUS_MANAGER.add_listener(StatusUpdate, self._on_server_status_change)
        self._on_server_status_change(StatusUpdate(STATUS_MANAGER.status, STATUS_MANAGER.message))

    def add_trigger_log_update_listener(self):
        """
        Adds the monitor on the beamline status, if this changes a monitor update is posted.
        """
        STATUS_MANAGER.add_listener(ErrorLogUpdate, self._on_error_log_update)
        self._on_error_log_update(ErrorLogUpdate(STATUS_MANAGER.error_log))

    def add_footprint_param_listeners(self):
        """
        Add listeners to parameters that affect the beam footprint.
        """
        parameters_to_monitor = set()
        for pv_name, (param_name, param_sort) in self._pv_manager.param_names_pv_names_and_sort():
            parameter = self._beamline.parameter(param_name)
            if BeamlineParameterGroup.FOOTPRINT_PARAMETER in parameter.group_names:
                parameters_to_monitor.add(parameter)
        for parameter in parameters_to_monitor:
            parameter.add_listener(ParameterReadbackUpdate, partial(self._update_footprint, FootprintSort.RBV))
            parameter.add_listener(ParameterSetpointReadbackUpdate,
                                   partial(self._update_footprint, FootprintSort.SP_RBV))

    def _add_trigger_on_engineering_correction_change(self):
        """
        Add all the triggers on engineering corrections.

        """
        def _update_corrections_pv(name, correction_update):
            """
            Update the driver engineering corrections PV with new value
            Args:
                name: name of the pv to update
                correction_update (CorrectionUpdate): the updated values
            Returns:
            """
            self._update_param_both_pv_and_pv_val(name,
                                                  correction_update.correction)
            self.setParam("{}:DESC".format(name), correction_update.description)
            self.updatePVs()

        for driver, pv_name in list(self._pv_manager.drivers_pv.items()):
            driver.add_listener(CorrectionUpdate, partial(_update_corrections_pv, pv_name))
            last_val = driver.listener_last_value(CorrectionUpdate)
            if last_val is None:
                last_val = CorrectionUpdate(float("NaN"), driver.correction_description)
            _update_corrections_pv(pv_name, last_val)
