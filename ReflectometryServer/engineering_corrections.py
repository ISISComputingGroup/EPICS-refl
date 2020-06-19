"""
Engineering correction to positions.
"""
import abc
import csv
import logging
import os
from collections import namedtuple
from contextlib import contextmanager
from typing import Dict, Optional

import numpy as np
import six
from attr import dataclass
from pcaspy import Severity
from scipy.interpolate import griddata

from ReflectometryServer import beamline_configuration, BeamlineMode
from ReflectometryServer.beamline import ActiveModeUpdate
from ReflectometryServer.server_status_manager import STATUS_MANAGER, ProblemInfo
from server_common.observable import observable

logger = logging.getLogger(__name__)


# The column name in the engineering correction interpolation data file to label the column which contains the
# IOCDriver's setpoint values
COLUMN_NAME_FOR_DRIVER_SETPOINT = "DRIVER"


@dataclass
class CorrectionUpdate:
    """
    Type for correction updates
    """
    correction: float  # amount value is corrected by
    description: str  # description of correction


@dataclass
class CorrectionRecalculate:
    """
    Correction has changed and the values need to calculating
    """
    reason_for_recalculate: str  # reason that we need to recalculate


@six.add_metaclass(abc.ABCMeta)
@observable(CorrectionUpdate, CorrectionRecalculate)
class EngineeringCorrection:
    """
    Base class for all engineering correction
    """

    def __init__(self, description):
        """
        Constructor.
        Args:
            description: initial description of the correction
        """
        self.description = description

    @abc.abstractmethod
    def to_axis(self, setpoint):
        """
        Correct a value sent to an axis using the correction
        Args:
            setpoint: setpoint to use to calculate correction

        Returns: the corrected value

        """

    @abc.abstractmethod
    def from_axis(self, value, setpoint):
        """
        Correct a value from the axis using the correction
        Args:
            value: value to correct
            setpoint: setpoint to use to calculate correction; if None setpoint has not been set yet

        Returns: the corrected value
        """

    def init_from_axis(self, setpoint):
        """
        Get a value from the axis without a setpoint. This may be possible in a small number of cases. If not this
        should return EngineeringCorrectionNotPossible
        Args:
            setpoint: value to convert from the axis as an initial value,

        Returns:
            the corrected value; EngineeringCorrectionNotPossible if this is not possible
        """
        return self.from_axis(setpoint, None)


@six.add_metaclass(abc.ABCMeta)
class SymmetricEngineeringCorrection(EngineeringCorrection):
    """
    Base class for engineering corrections which are symmetric for both to axis and from axis directions. Correction is
    added to the value when sent to an axis.
    """
    @abc.abstractmethod
    def correction(self, setpoint):
        """
        Returns: Correction to apply to the value
        """

    def to_axis(self, setpoint):
        """
        Correct a value sent to the the axis using the correction
        Args:
            setpoint: setpoint to use to calculate correction

        Returns: the corrected value

        """
        correction = self.correction(setpoint)
        self.trigger_listeners(CorrectionUpdate(correction, self.description))
        return setpoint + correction

    def from_axis(self, value, setpoint):
        """
        Correct a value read from the axis using the correction
        Args:
            value: value to correct
            setpoint: setpoint to use to calculate correction

        Returns: the corrected value

        """
        correction = self.correction(setpoint)
        self.trigger_listeners(CorrectionUpdate(correction, self.description))
        return value - correction


class NoCorrection(SymmetricEngineeringCorrection):
    """
    An engineering correction which does not change the value.
    """
    def correction(self, _):
        """

        Returns: a correction of zero (i.e. no change to the value)

        """
        return 0


class ConstantCorrection(SymmetricEngineeringCorrection):
    """
    A correction which adds a constant to the set point value when it is passed to the motor.
    """
    def __init__(self, offset):
        """
        Initialize.
        Args:
            offset: the offset to add to the motor when it is moved to
        """
        super(ConstantCorrection, self).__init__("Constant Correction")
        self._offset = offset

    def correction(self, _):
        """

        Returns: a constant correction value.

        """
        return self._offset

    def init_from_axis(self, setpoint):
        """
        Get a value from the axis without a setpoint. This may be possible in a small number of cases. If not this
        should return EngineeringCorrectionNotPossible
        Args:
            setpoint: value to convert from the axis as an initial value,

        Returns:
            the corrected value; EngineeringCorrectionNotPossible if this is not possible
        """
        return self.from_axis(setpoint, None)


class UserFunctionCorrection(SymmetricEngineeringCorrection):
    """
    A correction which is calculated from a user function.
    """
    def __init__(self, user_correction_function, *beamline_parameters):
        """
        Initialise.
        Args:
            user_correction_function (func): function which when called with the set point for this driver and any
                additional beamline parameters returns a constant which is added to that set point when that setpoint
                is sent to an IOC and is removed from the read-back when that read-back is read from the IOC
            beamline_parameters (ReflectometryServer.parameters.BeamlineParameter): beamline parameters to use in the
                user function, listed in the order they should be used in the user function
        """
        super(UserFunctionCorrection, self).__init__(
            "User function correction {}".format(user_correction_function.__name__))
        self._user_correction_function = user_correction_function
        self._beamline_parameters = beamline_parameters

    def correction(self, setpoint):
        """
        Correction as calculated by the provided user function.
        Args:
            setpoint: setpoint to use to calculate correction
        Returns: the correction calculated using the users function.
        """
        try:
            return self._user_correction_function(setpoint, *[param.sp_rbv for param in self._beamline_parameters])
        except Exception as ex:
            if setpoint is None or None in [param.sp_rbv for param in self._beamline_parameters]:
                non_initialised_params = [param.name for param in self._beamline_parameters if param.sp_rbv is None]
                STATUS_MANAGER.update_error_log(
                    "Engineering correction, '{}', raised exception '{}' is this because you have not coped with "
                    "non-autosaved value, {}".format(self.description, ex, non_initialised_params))
                STATUS_MANAGER.update_active_problems(
                    ProblemInfo("Invalid engineering correction (uses non autosaved value?)", self.description,
                                Severity.MINOR_ALARM))

            else:
                STATUS_MANAGER.update_error_log(
                    "Engineering correction, '{}', raised exception '{}' ".format(self.description, ex))
                STATUS_MANAGER.update_active_problems(
                    ProblemInfo("Engineering correction throws exception", self.description, Severity.MINOR_ALARM))

        return 0


class GridDataFileReader:
    """
    Read a file with point data in.
    """
    def __init__(self, filename):
        """
        Initialise.
        Args:
            filename: filename of file to read
        """
        self._filename = filename
        self.variables = None  # names of the variables that are being used type: list[str]
        self.points = None  # the points where the corrections are defined type: ndarray
        self.corrections = None  # the data corrections type: ndarray

    def read(self):
        """
        Perform the read of the file. Storing points in this instance of the class.
        """
        with self._open_file(self._filename) as correction_file:
            reader = csv.reader(correction_file, strict=True)
            try:
                self._read_header(next(reader))
                self._read_data(reader)
            except (csv.Error, ValueError) as e:
                raise IOError("Problem with data in '{}', line {} error {}".format(self._filename, reader.line_num, e))
            except StopIteration:
                raise IOError("No data found in file for the grid data engineering correction '{}'".format(
                    self._filename))

    def _read_data(self, reader):
        """
        Read data from the cvs file reader and store as numpy arrays in points and corrections
        Args:
            reader: cvs file reader

        Returns:
        """
        points = []
        corrections = []
        for row in reader:
            if len(row) != len(self.variables) + 1:
                raise IOError("Line {} should have the same number of entries as the header in "
                              "file '{}'".format(reader.line_num, self._filename))
            data_as_float = [float(item) for item in row]
            points.append(data_as_float[:-1])
            corrections.append(data_as_float[-1])
        self.points = np.array(points)
        self.corrections = np.array(corrections)

    def _read_header(self, row):
        """
        Read the header row and places it in variables
        Args:
            row: row to get header out of
        Returns:
        """
        self.variables = [header.strip() for header in row[:-1]]
        if len(self.variables) < 1:
            raise IOError(
                "Header of file should be 'parameter names, correction' in file '{}'".format(
                    self._filename))

    @staticmethod
    @contextmanager
    def _open_file(filename):
        """
        Open the file as a context.
        Args:
            filename: filename to open

        Yields:
            file
        """
        full_path = os.path.join(beamline_configuration.REFL_CONFIG_PATH, filename)
        if not os.path.isfile(full_path):
            raise IOError("No such file for interpolation 1D engineering correction '{}'".format(full_path))
        with open(full_path) as correction_file:
            yield correction_file


class _DummyBeamlineParameter:
    """
    A dummy beamline parameter which returns the axis setpoint to make the list of beamline parameters easy to construct
    """
    def __init__(self):
        self.sp_rbv = 0
        self.name = COLUMN_NAME_FOR_DRIVER_SETPOINT


class InterpolateGridDataCorrectionFromProvider(SymmetricEngineeringCorrection):
    """
    Generate a interpolated correction from a table of values.
    """

    def __init__(self, grid_data_provider, *beamline_parameters, description="Interpolated"):
        """
        Initialise.
        Args:
            grid_data_provider (GridDataFileReader): the provider of grid data
            beamline_parameters (ReflectometryServer.parameters.BeamlineParameter): beamline parameters to use in the
                interpolation
        """
        super(InterpolateGridDataCorrectionFromProvider, self).__init__(description)
        self._grid_data_provider = grid_data_provider
        self._grid_data_provider.read()
        self.set_point_value_as_parameter = _DummyBeamlineParameter()
        self._beamline_parameters = [self._find_parameter(variable, beamline_parameters)
                                     for variable in self._grid_data_provider.variables]

        self._default_correction = 0

    def _find_parameter(self, parameter_name, beamline_parameters):
        """
        Find the beamline parameter in the beamline parameters list
        Args:
            parameter_name: name of the beamline parameter
            beamline_parameters: possible parameters

        Returns:
            special driver parameter if the name is driver otherwise the beamline parameter associated with the name
        """
        if parameter_name.upper() == COLUMN_NAME_FOR_DRIVER_SETPOINT:
            return self.set_point_value_as_parameter

        named_parameters = [beamline_parameter for beamline_parameter in beamline_parameters
                            if beamline_parameter.name.upper() == parameter_name.upper()]
        if len(named_parameters) != 1:
            parameter_names = [beamline_parameter.name for beamline_parameter in beamline_parameters]
            raise ValueError("Data for Interpolate Grid Data has column name '{}' which does not match either "
                             "'{}' or one of the beamline parameter '{}'".
                             format(parameter_name, COLUMN_NAME_FOR_DRIVER_SETPOINT, parameter_names))
        return named_parameters[0]

    def correction(self, setpoint):
        """
        Correction as interpolated from the grid data provided
        Args:
            setpoint: setpoint to use to calculate correction
        Returns: the correction calculated using the grid data.
        """
        self.set_point_value_as_parameter.sp_rbv = setpoint
        evaluation_point = [param.sp_rbv for param in self._beamline_parameters]
        if None in evaluation_point:
            non_initialised_params = [param.name for param in self._beamline_parameters if param.sp_rbv is None]
            STATUS_MANAGER.update_error_log("Engineering correction, '{}', evaluated for non-autosaved value, {}"
                                            .format(self.description, non_initialised_params))
            STATUS_MANAGER.update_active_problems(
                ProblemInfo("Engineering correction evaluated for non-autosaved value", self.description,
                            Severity.MINOR_ALARM))

            interpolated_value = [0.0]
        else:
            interpolated_value = griddata(self._grid_data_provider.points, self._grid_data_provider.corrections,
                                          evaluation_point, 'linear', self._default_correction)
        return interpolated_value[0]


class InterpolateGridDataCorrection(InterpolateGridDataCorrectionFromProvider):
    """
    Generate a interpolated correction from a file containing a table of values.
    """

    def __init__(self, filename, *beamline_parameters):
        super(InterpolateGridDataCorrection, self).__init__(GridDataFileReader(filename), *beamline_parameters,
                                                            description="Interpolated from file {}".format(filename))


class ModeSelectCorrection(EngineeringCorrection):
    """
    This will select an engineering correction based on the current mode.
    """

    def __init__(self, default_correction: EngineeringCorrection,
                 corrections_for_mode: Dict[BeamlineMode, EngineeringCorrection]):
        """
        Initialisation.
        Args:
            default_correction: correction to use if there is not one specified for the mode
            corrections_for_mode: dictionary of which engineering correction to use in each mode
        """
        super(ModeSelectCorrection, self).__init__("Mode Selected")
        self._corrections_for_mode = corrections_for_mode
        self._default_correction = default_correction
        self._set_correction(None)

    def set_observe_mode_change_on(self, mode_changer):
        """
        Allow this correction to listen to mode change events from the mode_changer
        Args:
            mode_changer: object that can be observed for mode change events
        """
        mode_changer.add_listener(ActiveModeUpdate, self._mode_updated)

    def _mode_updated(self, update: ActiveModeUpdate):
        """
        Update the correction that this correction uses based on mode
        Args:
            update: the mode update event
        """
        self._set_correction(update.mode)
        self.trigger_listeners(CorrectionRecalculate("mode change"))

    def _set_correction(self, mode: Optional[BeamlineMode]):
        """
        Sets the correction that is being used based on the mode
        Args:
            mode: mode to use; None for use default
        """
        self._correction = self._corrections_for_mode.get(mode, self._default_correction)
        self.description = "Mode Selected: {}".format(self._correction.description)

    def from_axis(self, value, setpoint):
        """
        Correct a value from the axis using the correction for the mode
        Args:
            value: value to correct
            setpoint: setpoint to use to calculate correction; if None setpoint has not been set yet

        Returns: the corrected value
        """
        correction = self._correction.from_axis(value, setpoint)
        self.trigger_listeners(CorrectionUpdate(correction, self.description))
        return correction

    def to_axis(self, setpoint):
        """
        Correct a value sent to an axis using the correction based on the mode
        Args:
            setpoint: setpoint to use to calculate correction

        Returns: the corrected value
        """
        correction = self._correction.to_axis(setpoint)
        self.trigger_listeners(CorrectionUpdate(correction, self.description))
        return correction

    def init_from_axis(self, setpoint):
        """
        Get a value from the axis without a setpoint from the correction for this mode
        Args:
            setpoint: value to convert from the axis as an initial value,

        Returns:
            the corrected value; EngineeringCorrectionNotPossible if this is not possible
        """
        correction = self._correction.init_from_axis(setpoint)
        self.trigger_listeners(CorrectionUpdate(correction, self.description))
        return correction
