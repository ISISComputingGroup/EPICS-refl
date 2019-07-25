"""
Engineering correction to positions.
"""
import abc
import logging

import six

logger = logging.getLogger(__name__)


ENGINEERING_CORRECTION_NOT_POSSIBLE = "EnginerringCorrectionNotPossible"


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
        should return EnginerringCorrectionNotPossible
        Args:
            value: value to convert from the axis as an inital value,

        Returns:
            the corrected value; EnginerringCorrectionNotPossible if this is not possible
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
        should return EnginerringCorrectionNotPossible
        Args:
            value: value to convert from the axis as an inital value,

        Returns:
            the corrected value; EnginerringCorrectionNotPossible if this is not possible
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
        should return EnginerringCorrectionNotPossible
        Args:
            value: value to convert from the axis as an inital value,

        Returns:
            the corrected value; EnginerringCorrectionNotPossible if this is not possible
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
