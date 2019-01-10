from math import sin, tan, atan, degrees, radians, pi
import itertools

S1_ID = "SLIT1"
S2_ID = "SLIT2"
S3_ID = "SLIT3"
S4_ID = "SLIT4"
SA_ID = "SAMPLE"


class FootprintSetup(object):
    def __init__(self, pos_s1, pos_s2, pos_s3, pos_s4, pos_sample, s1vg, s2vg, s3vg, s4vg, theta, lambda_min, lambda_max):
        """
        Args:
            pos_s1: Z Position of slit 1 (along the beam)
            pos_s2: Z Position of slit 2 (along the beam)
            pos_s3: Z Position of slit 3 (along the beam)
            pos_s4: Z Position of slit 4 (along the beam)
            pos_sample: Z Position of the sample point (along the beam)
            s1vg(ReflectometryServer.parameters.SlitGapParameter): Vertical gap parameter for slit 1
            s2vg(ReflectometryServer.parameters.SlitGapParameter): Vertical gap parameter for slit 2
            s3vg(ReflectometryServer.parameters.SlitGapParameter): Vertical gap parameter for slit 3
            s4vg(ReflectometryServer.parameters.SlitGapParameter): Vertical gap parameter for slit 4
            theta(ReflectometryServer.parameters.AngleParameter): Paramater for the beam incident angle Theta
            lambda_min: Minimum lambda for this beamline
            lambda_max: Maximum lambda for this beamline
        """
        self.lambda_min = float(lambda_min)
        self.lambda_max = float(lambda_max)
        self.theta = theta
        self.sample_length = 200.0
        self.positions = {S1_ID: 0.0,
                          S2_ID: float(pos_s2 - pos_s1),
                          S3_ID: float(pos_s3 - pos_s1),
                          S4_ID: float(pos_s4 - pos_s1),
                          SA_ID: float(pos_sample - pos_s1),
                          }
        self.gap_params = {S1_ID: s1vg,
                           S2_ID: s2vg,
                           S3_ID: s3vg,
                           S4_ID: s4vg,
                           }


class BlankFootprintSetup(FootprintSetup):
    """
    Blank footprint setup for when none is given in the configuration file.
    """
    def __init__(self):
        super(BlankFootprintSetup, self).__init__(0, 0, 0, 0, 0, None, None, None, None, None, 0, 0)


class FootprintCalculator(object):
    """
    Calculator for the beam footprint and resolution.
    """

    def __init__(self, setup):
        super(FootprintCalculator, self).__init__()
        self.setup = setup
        self.update_gaps()

    def get_param_value(self, param):
        raise NotImplemented("This must be implemented in the sub class")

    def update_gaps(self):
        """
        Updates the value for each slit gap.
        """
        self.set_gap(SA_ID, self.setup.sample_length)
        for key, gap_param in self.setup.gap_params.iteritems():
            self.set_gap(key, self.get_param_value(gap_param))

    def theta(self):
        """
        Returns: The current theta parameter value.
        """
        return self.get_param_value(self.setup.theta)

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
        return self.gaps[SA_ID] * sin(radians(self.theta()))

    def calc_equivalent_gap_by_penumbra(self):
        """
        Calculate the equivalent slit gap of the sample based on the size of the penumbra at the sample.

        Returns: The equivalent slit gap size in mm
        """
        return (((self.distance(S1_ID, SA_ID) * (self.gaps[S1_ID] + self.gaps[S2_ID])) / (2 * self.distance(S1_ID, S2_ID))) - (self.gaps[S1_ID] / 2)) * 2

    def calc_footprint(self):
        """
        Calculate the footprint of the beam penumbra at the sample.

        Returns: The penumbra footprint in mm
        """
        self.update_gaps()
        return self.calc_equivalent_gap_by_penumbra() / sin(radians(self.theta()))

    def calc_footprint_umbra(self):
        """
        Calculate the footprint of the beam umbra at the sample.

        Returns: The umbra footprint in mm
        """
        self.update_gaps()
        return self.gaps[S2_ID] / sin(radians(self.theta()))

    def get_sample_slit_gap_equivalent(self):
        """
        Get the slit gap equivalent in size to the sample reflection. Either based on the size of the sample, or the
        size of the penumbra, whichever is smaller.

        Returns: The equivalent slit size of the sample reflection
        """
        if self.gaps[SA_ID] < self.calc_footprint():
            return self.calc_equivalent_gap_by_sample_size()
        else:
            return self.calc_equivalent_gap_by_penumbra()

    def get_gap(self, comp):
        """
        Get the gap size of a slit. For the sample, an equivalent is calculated and returned.

        Args:
            comp (String): The key of the component for which to get the gap size
            
        Returns: The gap size of the component or its equivalent for the sample reflection.
        """
        if comp is SA_ID:
            return self.get_sample_slit_gap_equivalent()
        else:
            return self.gaps[comp]

    def set_gap(self, key, val):
        """
        Set the gap size of a component in the model.

        Args:
            key (String): The key of the component to set the gap size on
            val (float): The new gap size.
        """
        self.gaps[key] = float(val)

    def calc_resolution(self, comp1, comp2):
        """
        Calculate the beam resolution for a given section of the beamline as identified by the components at its start
        and end.

        Args:
            comp1 (String): The key for the first beamline component
            comp2 (String): The key for the second beamline component

        Returns: The resolution for the given beamline section
        """
        comp1_gap = self.get_gap(comp1)
        comp2_gap = self.get_gap(comp2)
        res = atan((comp1_gap + comp2_gap) / self.distance(comp1, comp2))
        return (res / (2 * tan(radians(self.theta())))) * 100

    def calc_min_resolution(self):
        """
        Calculate the beam resolution for each segment of the beamline and out of those return the minimum.

        Returns: The resolution of the beam in mm
        """
        result = []
        self.update_gaps()
        for i in range(len(self.setup.positions.keys())-1):
            start_comp = self.setup.positions.keys()[i]
            end_comps = self.setup.positions.keys()[i+1:]
            component_pairs = itertools.product([start_comp], end_comps)
            for pair in component_pairs:
                result.append(self.calc_resolution(pair[0], pair[1]))
        return min(result)

    def calc_q_min(self):
        """
        Calculate the minimum Q that can be measured with the current beamline setup.

        Returns: The minimum measurable Q
        """
        self.update_gaps()
        q_min = 4 * pi * sin(radians(self.theta())) / self.setup.lambda_max
        return q_min

    def calc_q_max(self):
        """
        Calculate the maximum Q that can be measured with the current beamline setup.

        Returns: The maximum measurable Q
        """
        self.update_gaps()
        q_max = 4 * pi * sin(radians(self.theta())) / self.setup.lambda_min
        return q_max

    # TODO currently unused. check this is right
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
        sv1 = 2 * self.distance(S1_ID, SA_ID) * tan(resolution * theta_deg) - footprint * sin(theta_deg)
        sv2 = self.distance(S1_ID, S2_ID) * (footprint * sin(theta_deg)) / self.distance(S1_ID, SA_ID) - sv1
        return sv1, sv2


class FootprintCalculatorSetpoint(FootprintCalculator):
    """
    Calculates the footprint based on the setpoint values of beamline parameters.
    """
    def __init__(self, setup):
        """
        Args:
            setup (ReflectometryServer.footprint_calc.FootprintSetup): The footprint calculation setup
        """
        super(FootprintCalculatorSetpoint, self).__init__(setup)

    def get_param_value(self, param):
        """
        Returns: The setpoint value of a given parameter
        """
        return param.sp


class FootprintCalculatorSetpointReadback(FootprintCalculator):
    """
    Calculates the footprint based on the setpoint readback values of beamline parameters.
    """
    def __init__(self, setup):
        """
        Args:
            setup (ReflectometryServer.footprint_calc.FootprintSetup): The footprint calculation setup
        """
        super(FootprintCalculatorSetpointReadback, self).__init__(setup)

    def get_param_value(self, param):
        return param.sp_rbv


class FootprintCalculatorReadback(FootprintCalculator):
    """
    Calculates the footprint based on the readback values of beamline parameters.
    """
    def __init__(self, setup):
        """
        Args:
            setup (ReflectometryServer.footprint_calc.FootprintSetup): The footprint calculation setup
        """
        super(FootprintCalculatorReadback, self).__init__(setup)

    def get_param_value(self, param):
        """
        Returns: The readback value of a given parameter
        """
        return param.rbv
