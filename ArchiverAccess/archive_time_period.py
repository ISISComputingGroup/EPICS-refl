from datetime import datetime


class ArchiveTimePeriod(object):
    """
    A time period.
    """

    def __init__(self, start_time, delta, point_count):
        """
        Construct a time period.

        Args:
            start_time(datetime): the start time of the period (this is rounded down to the nearest millisecond)
            delta: the delta of each point within a period
            point_count: the point count of the period
        """
        self.start_time = start_time.replace(microsecond=0)
        self.period = delta
        self.point_count = point_count

    @property
    def end_time(self):
        """

        Returns: the end time of the period
        """
        return self.start_time + self.period * self.point_count

    def get_time_after(self, periods_count):
        """

        Args:
            periods_count: number of deltas that have passed in the period

        Returns: the current ime in the period

        """
        return self.start_time + self.period * periods_count
