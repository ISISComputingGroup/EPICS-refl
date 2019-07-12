"""
Engineering correction to positions.
"""
import abc
import logging

import six

logger = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class EngineeringCorrection:
    """
    Base class for all engineering correction
    """

    @abc.abstractmethod
    def to_axis(self, value):
        """
        Correct a value sent to an axis using the correction
        Args:
            value: value to correct

        Returns: the corrected value

        """

    @abc.abstractmethod
    def from_axis(self, value):
        """
        Correct a value from the axis using the correction
        Args:
            value: value to correct

        Returns: the corrected value

        """


@six.add_metaclass(abc.ABCMeta)
class SymmetricEngineeringCorrection(EngineeringCorrection):
    """
    Base class for engineering correction which are symmetric for from component and from axis. Correction is add to
    the value when sent to an axis.
    """

    @abc.abstractmethod
    def correction(self):
        """
        Returns: Correction to apply to the value
        """

    def to_axis(self, value):
        """
        Correct a value sent to the the axis using the correction
        Args:
            value: value to correct

        Returns: the corrected value

        """
        return value + self.correction()

    def from_axis(self, value):
        """
        Correct a value from the axis using the correction
        Args:
            value: value to correct

        Returns: the corrected value

        """
        return value - self.correction()


class NoCorrection(SymmetricEngineeringCorrection):
    """
    An engineering correction which does not change the value.
    """
    def correction(self):
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
        self._offset = offset

    def correction(self):
        """

        Returns: no correction

        """
        return self._offset
