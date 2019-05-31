"""
Driver for the reflectometry server.
"""
from functools import partial

from pcaspy import Driver, Alarm, Severity

from ReflectometryServer.ChannelAccess.pv_manager import PvSort, BEAMLINE_MODE, VAL_FIELD, BEAMLINE_STATUS, \
    BEAMLINE_MESSAGE, SP_SUFFIX, FootprintSort, FP_TEMPLATE, DQQ_TEMPLATE, QMIN_TEMPLATE, QMAX_TEMPLATE, \
    convert_from_epics_pv_value
from ReflectometryServer.parameters import BeamlineParameterGroup
from server_common.utilities import compress_and_hex


class ReflectometryDriver(Driver):
    """
    The driver which provides an interface for the reflectometry server to channel access by creating PVs and processing
    incoming CA get and put requests.
    """
    def __init__(self, server, beamline, pv_manager):
        """
        The Constructor.
        Args:
            server: The PCASpy server.
            beamline(ReflectometryServer.beamline.Beamline): The beamline configuration.
            pv_manager(ReflectometryServer.ChannelAccess.pv_manager.PVManager): The manager mapping PVs to objects in
                the beamline.
        """
        super(ReflectometryDriver, self).__init__()

        self._beamline = beamline
        self._ca_server = server
        self._pv_manager = pv_manager
        self._footprint_manager = beamline.footprint_manager

        for reason in self._pv_manager.PVDB.keys():
            self.setParamStatus(reason, severity=Severity.NO_ALARM, alarm=Alarm.NO_ALARM)

        self.update_monitors()

        self.add_param_listeners()
        self.add_trigger_active_mode_change_listener()
        self.add_trigger_status_change_listener()
        self.add_footprint_param_listeners()

    def read(self, reason):
        """
        Processes an incoming caget request.
        :param reason: The PV that is being read.
        :return: The value associated to this PV
        """
        if self._pv_manager.is_param(reason):
            param_name, param_sort = self._pv_manager.get_param_name_and_sort_from_pv(reason)
            param = self._beamline.parameter(param_name)
            value = param_sort.get_from_parameter(param)
            return value

        elif self._pv_manager.is_beamline_mode(reason):
            return self._beamline_mode_value(self._beamline.active_mode)

        elif self._pv_manager.is_beamline_move(reason):
            return self._beamline.move

        elif self._pv_manager.is_tracking_axis(reason):
            return compress_and_hex(self.getParam(reason))

        elif self._pv_manager.is_beamline_status(reason):
            beamline_status_enums = self._pv_manager.PVDB[BEAMLINE_STATUS]["enums"]
            new_value = beamline_status_enums.index(self._beamline.status.display_string)
            #  Set the value so that the error condition is set
            self.setParam(reason, new_value)
            return new_value

        elif self._pv_manager.is_beamline_message(reason):
            return self._beamline.message
        elif self._pv_manager.is_sample_length(reason):
            return self._footprint_manager.get_sample_length()
        else:
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
        status = True
        if self._pv_manager.is_param(reason):
            param_name, param_sort = self._pv_manager.get_param_name_and_sort_from_pv(reason)
            param = self._beamline.parameter(param_name)
            if param_sort == PvSort.MOVE:
                param.move = 1
            elif param_sort == PvSort.SP:
                param.sp = convert_from_epics_pv_value(param.parameter_type, value)
            elif param_sort == PvSort.SET_AND_NO_MOVE:
                param.sp_no_move = convert_from_epics_pv_value(param.parameter_type, value)
        elif self._pv_manager.is_beamline_move(reason):
            self._beamline.move = 1
        elif self._pv_manager.is_beamline_mode(reason):
            try:
                beamline_mode_enums = self._pv_manager.PVDB[BEAMLINE_MODE]["enums"]
                self._beamline.active_mode = beamline_mode_enums[value]
                self._update_param(reason, value)
            except ValueError:
                print("Invalid value entered for mode. (Possible modes: {})".format(
                    ",".join(self._beamline.mode_names)))
                status = False
        elif self._pv_manager.is_sample_length(reason):
            self._footprint_manager.set_sample_length(value)
        else:
            print("Error: PV is read only")
            status = False

        if status:
            self._update_param(reason, value)
            self.update_monitors()
        return status

    def update_monitors(self):
        """
        Updates the PV values for each parameter so that changes are visible to monitors.
        """
        # with self.monitor_lock:
        for pv_name, (param_name, param_sort) in self._pv_manager.param_names_pvnames_and_sort():
            parameter = self._beamline.parameter(param_name)
            self._update_param(pv_name, param_sort.get_from_parameter(parameter))
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
        self._update_param(FP_TEMPLATE.format(prefix), self._footprint_manager.get_footprint(sort))
        self._update_param(DQQ_TEMPLATE.format(prefix), self._footprint_manager.get_resolution(sort))
        self._update_param(QMIN_TEMPLATE.format(prefix), self._footprint_manager.get_q_min(sort))
        self._update_param(QMAX_TEMPLATE.format(prefix), self._footprint_manager.get_q_max(sort))
        self.updatePVs()

    def _update_param(self, pv_name, value):
        """
        Update a parameter value (both it and .VAL)

        Args:
            pv_name: name of the pv
            value: value of the parameter
        """
        self.setParam(pv_name, value)
        self.setParam(pv_name + VAL_FIELD, value)

    def _update_param_listener(self, pv_name, value):
        """
        Listener for responding to updates from the command line parameter
        Args:
            pv_name: name of the pv
            value: new value
        """
        self._update_param(pv_name, value)
        self.updatePVs()

    def add_param_listeners(self):
        """
        Add listeners to beamline parameter changes, which update pvs in the server
        """
        for pv_name, (param_name, param_sort) in self._pv_manager.param_names_pvnames_and_sort():
            parameter = self._beamline.parameter(param_name)
            parameter.add_init_listener(partial(self._update_param_listener, pv_name))
            if param_sort == PvSort.RBV:
                parameter.add_rbv_change_listener(partial(self._update_param_listener, pv_name))
            if param_sort == PvSort.SP_RBV:
                parameter.add_sp_rbv_change_listener(partial(self._update_param_listener, pv_name))

    def add_trigger_active_mode_change_listener(self):
        """
        Adds the monitor on the active mode, if this changes a monitor update is posted.
        """
        def _bl_mode_change(mode):
            mode_value = self._beamline_mode_value(mode)
            self._update_param(BEAMLINE_MODE, mode_value)
            self._update_param(BEAMLINE_MODE + SP_SUFFIX, mode_value)
            self.updatePVs()
        self._beamline.add_active_mode_change_listener(_bl_mode_change)

    def add_trigger_status_change_listener(self):
        """
        Adds the monitor on the beamline status, if this changes a monitor update is posted.
        """
        def _bl_status_change(status, message):
            beamline_status_enums = self._pv_manager.PVDB[BEAMLINE_STATUS]["enums"]
            status_id = beamline_status_enums.index(status.display_string)
            self._update_param(BEAMLINE_STATUS, status_id)
            self._update_param(BEAMLINE_MESSAGE, message)
            self.updatePVs()
        self._beamline.add_status_change_listener(_bl_status_change)

    def add_footprint_param_listeners(self):
        """
        Add listeners to parameters that affect the beam footprint.
        """
        parameters_to_monitor = set()
        for pv_name, (param_name, param_sort) in self._pv_manager.param_names_pvnames_and_sort():
            parameter = self._beamline.parameter(param_name)
            if BeamlineParameterGroup.FOOTPRINT_PARAMETER in parameter.group_names:
                parameters_to_monitor.add(parameter)
        for parameter in parameters_to_monitor:
            parameter.add_rbv_change_listener(partial(self._update_footprint, FootprintSort.RBV))
            parameter.add_sp_rbv_change_listener(partial(self._update_footprint, FootprintSort.SP_RBV))
