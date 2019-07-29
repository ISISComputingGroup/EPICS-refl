"""
Engineering correction to positions.
"""
import abc
import csv
import logging
import os
from contextlib import contextmanager

import numpy as np
import six
from scipy.interpolate import griddata

from ReflectometryServer import beamline_configuration

logger = logging.getLogger(__name__)


# constant used to indicate that a value is not allowed to be used
ENGINEERING_CORRECTION_NOT_POSSIBLE = "EngineeringCorrectionNotPossible"


# The column name in the engineering correction interpolation data file to label the column which contains the
# IOCDriver's setpoint values
COLUMN_NAME_FOR_DRIVER_SETPOINT = "DRIVER"


@six.add_metaclass(abc.ABCMeta)
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
            setpoint: setpoint to use to calculate correction

        Returns: the corrected value
        """

    def init_from_axis(self, value):
        """
        Get a value from the axis without a setpoint. This may be possible in a small number of cases. If not this
        should return EngineeringCorrectionNotPossible
        Args:
            value: value to convert from the axis as an inital value,

        Returns:
            the corrected value; EngineeringCorrectionNotPossible if this is not possible
        """
        return ENGINEERING_CORRECTION_NOT_POSSIBLE


@six.add_metaclass(abc.ABCMeta)
class SymmetricEngineeringCorrection(EngineeringCorrection):
    """
    Base class for engineering correction which are symmetric for from component and from axis. Correction is add to
    the value when sent to an axis.
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
        return setpoint + self.correction(setpoint)

    def from_axis(self, value, setpoint):
        """
        Correct a value from the axis using the correction
        Args:
            value: value to correct
            setpoint: setpoint to use to calculate correction

        Returns: the corrected value

        """
        return value - self.correction(setpoint)


class NoCorrection(SymmetricEngineeringCorrection):
    """
    An engineering correction which does not change the value.
    """
    def correction(self, _):
        """

        Returns: no correction

        """
        return 0

    def init_from_axis(self, value):
        """
        Get a value from the axis without a setpoint. This may be possible in a small number of cases. If not this
        should return EngineeringCorrectionNotPossible
        Args:
            value: value to convert from the axis as an inital value,

        Returns:
            the corrected value; EngineeringCorrectionNotPossible if this is not possible
        """
        return value


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
        self._offset = offset

    def correction(self, _):
        """

        Returns: no correction

        """
        return self._offset

    def init_from_axis(self, value):
        """
        Get a value from the axis without a setpoint. This may be possible in a small number of cases. If not this
        should return EngineeringCorrectionNotPossible
        Args:
            value: value to convert from the axis as an inital value,

        Returns:
            the corrected value; EngineeringCorrectionNotPossible if this is not possible
        """
        return self.from_axis(value, None)


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
                is sent to an IOC and is removed from the readback when that readback is read from the IOC
            beamline_parameters (ReflectometryServer.parameters.BeamlineParameter): beamline parameters to use in the
                user function, listed in the order they should be used in the user function
        """
        self._user_correction_function = user_correction_function
        self._beamline_parameters = beamline_parameters

    def correction(self, setpoint):
        """
        Correction
        Args:
            setpoint: setpoint to use to calculate correction
        Returns: the correction calculated using the users function.
        """

        return self._user_correction_function(setpoint, *[param.sp_rbv for param in self._beamline_parameters])


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
        fullpath = os.path.join(beamline_configuration.REFL_CONFIG_PATH, filename)
        if not os.path.isfile(fullpath):
            raise IOError("No such file for interpolation 1D engineering correction '{}'".format(fullpath))
        with open(fullpath) as correction_file:
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
        self._grid_data_provider = grid_data_provider
        self._grid_data_provider.read()
        self.set_point_value_as_parameter = _DummyBeamlineParameter()
        self._beamline_parameters = [self._find_parameter(variable, beamline_parameters)
                                     for variable in self._grid_data_provider.variables]

        self._default_correction = 0

    def _find_parameter(self, beamline_name, beamline_parameters):
        """
        Find the beamline parameter in the beamline parameters list
        Args:
            beamline_name: name of the bealmine parameter
            beamline_parameters: possible parameters

        Returns:
            special driver prameter if the name is driver otherise the beamline parameter associated with the name
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
        interpolated_value = griddata(self._grid_data_provider.points, self._grid_data_provider.corrections,
                                      evaluation_point, 'linear', self._default_correction)
        return interpolated_value[0]


class InterpolateGridDataCorrection(InterpolateGridDataCorrectionFromProvider):
    """
    Generate a interpolated correction from a file containing a table of values.
    """

    def __init__(self, filename, *beamline_parameters):
        super(InterpolateGridDataCorrection, self).__init__(GridDataFileReader(filename), *beamline_parameters)
