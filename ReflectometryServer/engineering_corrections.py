"""
Engineering correction to positions.
"""
import abc
import csv
import logging
import os
from collections import namedtuple
from contextlib import contextmanager

import numpy as np
import six
from scipy.interpolate import griddata

from ReflectometryServer import beamline_configuration
from ReflectometryServer.observable import observable

logger = logging.getLogger(__name__)


# The column name in the engineering correction interpolation data file to label the column which contains the
# IOCDriver's setpoint values
COLUMN_NAME_FOR_DRIVER_SETPOINT = "DRIVER"

# Type for correction updates
CorrectionUpdate = namedtuple("CorrectionUpdate", ["correction", "description"])


@six.add_metaclass(abc.ABCMeta)
@observable(CorrectionUpdate)
class EngineeringCorrection:
    """
    Base class for all engineering correction
    """

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
    Base class for engineering correction which are symmetric for from component and from axis. Correction is add to
    the value when sent to an axis.
    """

    def __init__(self):
        self.description = "Symmetric engineering correction"

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
        Correct a value from the axis using the correction
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

        Returns: no correction

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
        super(ConstantCorrection, self).__init__()
        self._offset = offset
        self.description = "Constant Correction"

    def correction(self, _):
        """

        Returns: no correction

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
        super(UserFunctionCorrection, self).__init__()
        self._user_correction_function = user_correction_function
        self._beamline_parameters = beamline_parameters
        self.description = "User function correction {}".format(user_correction_function.__name__)

    def correction(self, setpoint):
        """
        Correction
        Args:
            setpoint: setpoint to use to calculate correction
        Returns: the correction calculated using the users function.
        """
        try:
            return self._user_correction_function(setpoint, *[param.sp_rbv for param in self._beamline_parameters])
        except Exception as ex:
            if setpoint is None or None in [param.sp_rbv for param in self._beamline_parameters]:
                non_initialised_params = [param.name for param in self._beamline_parameters if param.sp_rbv is None]
                logger.error("Engineering correction, '{}', raised exception '{}' is this because you have not coped "
                             "with non-autosaved value, {}".format(self.description, ex, non_initialised_params))
            else:
                logger.error("Engineering correction, '{}', raised exception '{}' ".format(self.description, ex))
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


class InterpolateGridDataCorrectionFromProvider(SymmetricEngineeringCorrection):
    """
    Generate a interpolated correction from a table of values.
    """

    def __init__(self, grid_data_provider, *beamline_parameters):
        """
        Initialise.
        Args:
            grid_data_provider (GridDataFileReader): the provider of grid data
            beamline_parameters (ReflectometryServer.parameters.BeamlineParameter): beamline parameters to use in the
                interpolation
        """
        super(InterpolateGridDataCorrectionFromProvider, self).__init__()
        self._grid_data_provider = grid_data_provider
        self._grid_data_provider.read()
        self.set_point_value_as_parameter = _DummyBeamlineParameter()
        self._beamline_parameters = [self._find_parameter(variable, beamline_parameters)
                                     for variable in self._grid_data_provider.variables]

        self._default_correction = 0
        self.description = "Interpolated"

    def _find_parameter(self, beamline_name, beamline_parameters):
        """
        Find the beamline parameter in the beamline parameters list
        Args:
            beamline_name: name of the beamline parameter
            beamline_parameters: possible parameters

        Returns:
            special driver parameter if the name is driver otherwise the beamline parameter associated with the name
        """
        if beamline_name.upper() == COLUMN_NAME_FOR_DRIVER_SETPOINT:
            return self.set_point_value_as_parameter

        named_parameters = [beamline_parameter for beamline_parameter in beamline_parameters
                            if beamline_parameter.name.upper() == beamline_name.upper()]
        if len(named_parameters) != 1:
            parameter_names = [beamline_parameter.name for beamline_parameter in beamline_parameters]
            raise ValueError("Data for Interpolate Grid Data has column name '{}' which does not match either "
                             "'{}' or one of the beamline parameter '{}'".
                             format(beamline_name, COLUMN_NAME_FOR_DRIVER_SETPOINT, parameter_names))
        return named_parameters[0]

    def correction(self, setpoint):
        """
        Correction
        Args:
            setpoint: setpoint to use to calculate correction
        Returns: the correction calculated using the users function.
        """
        self.set_point_value_as_parameter.sp_rbv = setpoint
        evaluation_point = [param.sp_rbv for param in self._beamline_parameters]
        if None in evaluation_point:
            non_initialised_params = [param.name for param in self._beamline_parameters if param.sp_rbv is None]
            logger.error("Engineering correction, '{}', evaluated for non-autosaved value, {}".format(
                self.description, non_initialised_params))
            interpolated_value = [0]
        else:
            interpolated_value = griddata(self._grid_data_provider.points, self._grid_data_provider.corrections,
                                          evaluation_point, 'linear', self._default_correction)
        return interpolated_value[0]


class InterpolateGridDataCorrection(InterpolateGridDataCorrectionFromProvider):
    """
    Generate a interpolated correction from a file containing a table of values.
    """

    def __init__(self, filename, *beamline_parameters):
        super(InterpolateGridDataCorrection, self).__init__(GridDataFileReader(filename), *beamline_parameters)
        self.description = "Interpolated from file {}".format(filename)
