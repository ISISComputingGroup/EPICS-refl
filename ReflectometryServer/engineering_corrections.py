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

from ReflectometryServer import beamline_configuration

logger = logging.getLogger(__name__)


ENGINEERING_CORRECTION_NOT_POSSIBLE = "EngineeringCorrectionNotPossible"


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
            beamline_parameters (ReflectometryServer.parameters.BeamlineParameter):
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
        self.variables = None
        self.values = None
        self.corrections = None

    def read(self):
        """
        Perform the read of the file. Storing values in this instance of the class.
        """
        with self._open_file(self._filename) as correction_file:
            reader = csv.reader(correction_file, strict=True)
            try:
                self.variables = None
                values = []
                corrections = []
                for row in reader:
                    if self.variables is None:
                        self.variables = [header.strip() for header in row[:-1]]
                        if len(self.variables) < 1:
                            raise IOError(
                                "Header of file should be 'parameter names, correction' in file '{}'".format(
                                    self._filename))
                    else:
                        if len(row) != len(self.variables) + 1:
                            raise IOError("Line {} should have the same number of entries as the header in "
                                          "file '{}'".format(reader.line_num, self._filename))
                        data_as_float = [float(item) for item in row]
                        values.append(data_as_float[:-1])
                        corrections.append(data_as_float[-1])

            except (csv.Error, ValueError) as e:
                raise IOError("Problem with data in '{}', line {} error {}".format(self._filename, reader.line_num, e))
        if self.variables is None:
            raise IOError("No data found in file for the grid data engineering correction '{}'".format(self._filename))

        self.values = np.array(values)
        self.corrections = np.array(corrections)

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


class Interpolate1DCorrection(SymmetricEngineeringCorrection):
    """
    Generate a interpolated correction from a table of values.
    """

    def __init__(self, filename=None, grid_data_provider=None):
        """
        Initialise.
        Args:
            filename: filename to use; if None use the data_provider
            grid_data_provider: the provider of grid data; if None you the GridDataFileReader with given filename
        """
        if (filename is None) == (grid_data_provider is None):
            raise ValueError("{} needs either filename or file_reader set not both".format(self.__class__.__name__))
        if grid_data_provider is None:
            grid_data_provider = GridDataFileReader(filename)
        grid_data_provider.read()

    def correction(self, setpoint):
        """
        Correction
        Args:
            setpoint: setpoint to use to calculate correction
        Returns: the correction calculated using the users function.
        """

        return None
