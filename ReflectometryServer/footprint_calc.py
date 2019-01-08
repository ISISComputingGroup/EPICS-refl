from math import sin, tan, atan, degrees, radians, pi
import itertools

S1 = "POS_S1"
S2 = "POS_S2"
S3 = "POS_S3"
S4 = "POS_S4"
SA = "POS_SA"

NOT_A_NUMBER = "NaN"


class FootprintSetup(object):
    def __init__(self, pos_s1, pos_s2, pos_s3, pos_s4, pos_sa, lambda_min, lambda_max, theta):
        """
        :param pos_s1: Position of slit 1 along Z
        :param pos_s2: Position of slit 2 along Z
        :param pos_s3: Position of slit 3 along Z
        :param pos_s4: Position of slit 4 along Z
        :param pos_sa: Position of the sample point along Z
        :param lambda_min: Minimum lambda of the instrument
        :param lambda_max: Maximum lambda of the instrument
        :param theta(ReflectometryServer.parameters.AngleParameter): The parameter holding the incident beam angle
        """
        self.lambda_min = float(lambda_min)
        self.lambda_max = float(lambda_max)
        self.theta = theta
        self.positions = {S1: 0.0,
                          S2: float(pos_s2 - pos_s1),
                          S3: float(pos_s3 - pos_s1),
                          S4: float(pos_s4 - pos_s1),
                          SA: float(pos_sa - pos_s1),
                          }
        self.gaps = {S1: 40.0,
                     S2: 30.0,
                     S3: 30.0,
                     S4: 40.0,
                     SA: 200.0,
                     }


class BlankFootprintSetup(FootprintSetup):
    def __init__(self):
        super(BlankFootprintSetup, self).__init__(0, 0, 0, 0, 0, 0, 0, None)


class FootprintCalculator(object):
    """
    Calculator for the beam footprint and resolution.
    """

    def __init__(self, setup):
        super(FootprintCalculator, self).__init__()
        self.setup = setup

    def theta(self):
        raise NotImplemented("This must be implemented in the sub class")

    def distance(self, comp1, comp2):
        """
        Calculate the distance between two given beamline components along the beam direction.

        Args:
            comp1 (String): The key for the first beamline component
            comp2 (String): The key for the second beamline component

        Returns: The distance between the two components in mm
        """
        assert comp1, comp2 in self.setup.positions.keys()
        return abs(self.setup.positions[comp1] - self.setup.positions[comp2])

    def calc_equivalent_gap_by_sample_size(self):
        """
        Calculate the equivalent slit gap of the sample based on its size and the incident beam angle.

        Returns: The equivalent slit gap size in mm
        """
        return self.setup.gaps[SA] * sin(radians(self.theta()))

    def calc_equivalent_gap_by_penumbra(self):
        """
        Calculate the equivalent slit gap of the sample based on the size of the penumbra at the sample.

        Returns: The equivalent slit gap size in mm
        """
        return (((self.distance(S1, SA) * (self.setup.gaps[S1] + self.setup.gaps[S2])) / (2 * self.distance(S1, S2))) - (self.setup.gaps[S1] / 2)) * 2

    def calc_footprint(self):
        """
        Calculate the footprint of the beam penumbra at the sample.

        Returns: The penumbra footprint in mm
        """
        if self.theta():
            return self.calc_equivalent_gap_by_penumbra() / sin(radians(self.theta()))
        else:
            return NOT_A_NUMBER

    def calc_footprint_umbra(self):
        """
        Calculate the footprint of the beam umbra at the sample.

        Returns: The umbra footprint in mm
        """
        return self.setup.gaps[S2] / sin(radians(self.theta()))

    def get_sample_slit_gap_equivalent(self):
        """
        Get the slit gap equivalent in size to the sample reflection. Either based on the size of the sample, or the
        size of the penumbra, whichever is smaller.

        Returns: The equivalent slit size of the sample reflection
        """
        if self.setup.gaps[SA] < self.calc_footprint():
            return self.calc_equivalent_gap_by_sample_size()
        else:
            return self.calc_equivalent_gap_by_penumbra()

    def get_gap(self, comp):
        """
        Get the gap size of a slit. For the sample, an equivalent is calculated and returned.

        Args:
            comp (String): The key of the component for which to get the gap size
            theta (float): The incident beam angle
            
        Returns: The gap size of the component or its equivalent for the sample reflection.
        """
        if comp is SA:
            return self.get_sample_slit_gap_equivalent()
        else:
            return self.setup.gaps[comp]

    def set_gap(self, comp, val):
        """
        Set the gap size of a component in the model.

        Args:
            comp (String): The key of the component to set the gap size on
            val (float): The new gap size.
        """
        self.setup.gaps[comp] = float(val)

    def calc_resolution(self, comp1, comp2):
        """
        Calculate the beam resolution for a given section of the beamline as identified by the components at its start
        and end.

        Args:
            comp1 (String): The key for the first beamline component
            comp2 (String): The key for the second beamline component
            theta (float): The incident beam angle

        Returns: The resolution for the given beamline section
        """
        comp1_gap = self.get_gap(comp1)
        comp2_gap = self.get_gap(comp2)
        res = atan((comp1_gap + comp2_gap) / self.distance(comp1, comp2))
        return (res / (2 * tan(radians(self.theta())))) * 100

    def calc_min_resolution(self):
        if self.theta():
            result = []
            for i in range(len(self.setup.positions.keys())-1):
                start_comp = self.setup.positions.keys()[i]
                end_comps = self.setup.positions.keys()[i+1:]
                component_pairs = itertools.product([start_comp], end_comps)
                for pair in component_pairs:
                    result.append(self.calc_resolution(pair[0], pair[1]))
            return min(result)
        else:
            return NOT_A_NUMBER

    def calc_q_min(self):
        """
        Calculate the range of Q that can be measured with the current beamline setup.

        :param theta: The incident beam angle
        :return: the minimum and maximum Q that can be measured
        """
        if self.theta():
            q_min = 4 * pi * sin(radians(self.theta())) / self.setup.lambda_max
            return q_min
        else:
            return NOT_A_NUMBER

    def calc_q_max(self):
        """
        Calculate the range of Q that can be measured with the current beamline setup.

        :param theta: The incident beam angle
        :return: the minimum and maximum Q that can be measured
        """
        if self.theta():
            q_max = 4 * pi * sin(radians(self.theta())) / self.setup.lambda_min
            return q_max
        else:
            return NOT_A_NUMBER

    # TODO check this is right
    def calc_gaps(self, theta_rad, resolution, footprint):
        """
        Calculate the gap sizes for all slits needed to achieve a given resolution and footprint

        Args:
            theta_rad (float): The incident beam angle in radians
            resolution (float): The beam resolution
            footprint (float): The beam footprint in mm

        Returns: The slit gaps for slit 1 and 2
        """
        theta_deg = degrees(theta_rad)
        sv1 = 2 * self.distance(S1, SA) * tan(resolution * theta_deg) - footprint * sin(theta_deg)
        sv2 = self.distance(S1, S2) * (footprint * sin(theta_deg)) / self.distance(S1, SA) - sv1
        return sv1, sv2


class FootprintCalculatorSetpoint(FootprintCalculator):
    def __init__(self, setup):
        super(FootprintCalculatorSetpoint, self).__init__(setup)

    def theta(self):
        return self.setup.theta.sp


class FootprintCalculatorSetpointReadback(FootprintCalculator):
    def __init__(self, setup):
        super(FootprintCalculatorSetpointReadback, self).__init__(setup)

    def theta(self):
        return self.setup.theta.sp_rbv


class FootprintCalculatorReadback(FootprintCalculator):
    def __init__(self, setup):
        super(FootprintCalculatorReadback, self).__init__(setup)

    def theta(self):
        return self.setup.theta.rbv
