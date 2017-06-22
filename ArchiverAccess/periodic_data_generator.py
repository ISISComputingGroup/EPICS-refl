import collections


period_data_point = collections.namedtuple("period_data_point", "time values")
"""a single perioduc data point, essential all the values at a point in time"""


class PeriodicDataGenerator(object):
    """
    Generate the data as a set of periodic values.

    This changes the form of the data from the archiver_data from points in time when PVs changed to regular pv values.
    This snaps shots the value at the point of time required.
    """

    def __init__(self, start_time, period, point_count, archiver_data):
        """
        Constructor

        :param start_time: time at which the data should start
        :param period: period between data points
        :param point_count: the number of points to generate
        :param archiver_data: the archiver data source
        """
        self._start_time = start_time
        self._point_count = point_count
        self._archiver_data = archiver_data
        self._period = period

        self._archiver_changes_generator = self._archiver_data.changes_generator()

    def get_generator(self):
        """
        Get a generator which produces data points.

        :return: Generator for a data point which is a period_data_point tuple
        """
        current_values = self._archiver_data.initial_values()
        self._set_next_change()

        for current_point_count in range(self._point_count + 1):
            current_time = self._start_time + self._period * current_point_count
            current_values = self._get_values_at_time(current_values, current_time)

            yield period_data_point(current_time, current_values)

    def _get_values_at_time(self, initial_values, time):
        """
        Get the values for the given time by iterating through the changes in the values until the current change
        is after the needed change and updating the current values as we go.
        :param initial_values: the initial values
        :param time: the time that we want the values for
        :return: list of values at the wanted time
        """
        updated_list = list(initial_values)
        while self._next_change_time is not None and self._next_change_time <= time:
            updated_list[self._next_change_index] = self._next_change_value
            self._set_next_change()

        return updated_list

    def _set_next_change(self):
        """
        Get the next change in the change list
        :return:
        """
        try:
            self._next_change_time, self._next_change_index, self._next_change_value = \
                self._archiver_changes_generator.next()
        except StopIteration:
            self._next_change_time = None
