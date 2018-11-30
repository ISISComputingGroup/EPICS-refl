from math import sin, tan, atan, degrees, radians, pi
import itertools

S1 = "pos_s1"
S2 = "pos_s2"
S3 = "pos_s3"
S4 = "pos_s4"
SA = "pos_sa"


class FootprintCalculator:

    def __init__(self, pos_s1, pos_s2, pos_s3, pos_s4, pos_sa, lambda_min, lambda_max):
        self.positions = {S1: 0.0,
                          S2: float(pos_s2 - pos_s1),
                          S3: float(pos_s3 - pos_s1),
                          S4: float(pos_s4 - pos_s1),
                          SA: float(pos_sa - pos_s1),
                          }
        self.lambda_min = lambda_min
        self.lambda_max = lambda_max
        self.gaps = {S1: 40.0,
                     S2: 30.0,
                     S3: 30.0,
                     S4: 40.0,
                     SA: 200.0,
                     }

    def distance(self, comp1, comp2):
        """
        Calculate the distance between two given beamline components along the beam direction.

        Args:
            comp1 (String): The key for the first beamline component
            comp2 (String): The key for the second beamline component

        Returns: The distance between the two components in mm
        """
        assert comp1, comp2 in self.positions.keys()
        return abs(self.positions[comp1] - self.positions[comp2])

    def calc_equivalent_gap_by_sample_size(self, theta):
        """
        Calculate the equivalent slit gap of the sample based on its size and the incident beam angle.

        Args:
            theta (float): The incident beam angle

        Returns: The equivalent slit gap size in mm
        """
        return self.gaps[SA] * sin(radians(theta))

    def calc_equivalent_gap_by_penumbra(self):
        """
        Calculate the equivalent slit gap of the sample based on the size of the penumbra at the sample.

        Args:
            theta (float): The incident beam angle

        Returns: The equivalent slit gap size in mm
        """
        return (((self.distance(S1, SA) * (self.gaps[S1] + self.gaps[S2])) / (2 * self.distance(S1, S2))) - (self.gaps[S1] / 2)) * 2

    def calc_footprint_penumbra(self, theta):
        """
        Calculate the footprint of the beam penumbra at the sample.

        Args:
            theta (float): The incident beam angle

        Returns: The penumbra footprint in mm
        """
        return self.calc_equivalent_gap_by_penumbra() / sin(radians(theta))

    def calc_footprint_umbra(self, theta):
        """
        Calculate the footprint of the beam umbra at the sample.

        Args:
            theta (float): The incident beam angle

        Returns: The umbra footprint in mm
        """
        return self.gaps[S2] / sin(radians(theta))

    def get_sample_slit_gap_equivalent(self, theta):
        """
        Get the slit gap equivalent in size to the sample reflection. Either based on the size of the sample, or the
        size of the penumbra, whichever is smaller.

        Args:
            theta (float): The incident beam angle

        Returns: The equivalent slit size of the sample reflection
        """
        if self.gaps[SA] < self.calc_footprint_penumbra(theta):
            return self.calc_equivalent_gap_by_sample_size(theta)
        else:
            return self.calc_equivalent_gap_by_penumbra()

    def get_gap(self, comp, theta):
        """
        Get the gap size of a slit. For the sample, an equivalent is calculated and returned.

        Args:
            comp (String): The key of the component for which to get the gap size
            theta (float): The incident beam angle
            
        Returns: The gap size of the component or its equivalent for the sample reflection.
        """
        if comp is SA:
            return self.get_sample_slit_gap_equivalent(theta)
        else:
            return self.gaps[comp]

    def set_gap(self, comp, val):
        """
        Set the gap size of a component in the model.

        Args:
            comp (String): The key of the component to set the gap size on
            val (float): The new gap size.
        """
        self.gaps[comp] = float(val)

    def calc_resolution(self, comp1, comp2, theta):
        """
        Calculate the beam resolution for a given section of the beamline as identified by the components at its start
        and end.

        Args:
            comp1 (String): The key for the first beamline component
            comp2 (String): The key for the second beamline component
            theta (float): The incident beam angle

        Returns: The resolution for the given beamline section
        """
        comp1_gap = self.get_gap(comp1, theta)
        comp2_gap = self.get_gap(comp2, theta)
        res = atan((comp1_gap + comp2_gap) / self.distance(comp1, comp2))
        return (res / (2 * tan(radians(theta)))) * 100

    def calc_min_resolution(self, theta):
        result = []
        for i in range(len(self.positions.keys())-1):
            start_comp = self.positions.keys()[i]
            end_comps = self.positions.keys()[i+1:]
            component_pairs = itertools.product([start_comp], end_comps)
            for pair in component_pairs:
                result.append(self.calc_resolution(pair[0], pair[1], theta))
        return min(result)

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

    def calc_q_range(self, theta):
        q_min = 4 * pi * sin(radians(theta)) / self.lambda_max
        q_max = 4 * pi * sin(radians(theta)) / self.lambda_min
        return q_min, q_max