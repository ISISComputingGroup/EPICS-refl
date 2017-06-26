from datetime import timedelta, datetime

from server_common.mysql_abstraction_layer import SQLAbstraction

ERROR_PREFIX = "ERROR: "
VALUE_WHEN_ERROR_ON_RETRIEVAL = ERROR_PREFIX + "Data value can not be retrieved"


class ArchiverDataValue:
    def __init__(self, data_base_query_list):
        self.severity_id, self.status_id, self.num_val, self.float_val, self.str_val, self.array_val = data_base_query_list

    @property
    def value(self):
        if self.num_val is not None:
            return self.num_val
        elif self.float_val is not None:
            return self.float_val
        elif self.str_val is not None:
            return self.str_val
        else:
            return self.array_val

    def __str__(self):
        return str(self.value)

    def get_as_array(self):
        return [self.severity_id, self.status_id, self.num_val, self.float_val, self.str_val, self.array_val]

INITIAL_VALUES_QUERY = """
    SELECT severity_id, status_id, num_val, float_val, str_val, array_val
      FROM archive.sample 
     WHERE sample_id = (
        SELECT max(s.sample_id)
          FROM archive.sample s
         WHERE channel_id = (
                SELECT channel_id
                  FROM archive.channel
                 WHERE name = %s)
           AND s.smpl_time <= %s
     )
"""

GET_CHANGES_QUERY = """
    SELECT c.name, s.smpl_time, s.severity_id, s.status_id, s.num_val, s.float_val, s.str_val, s.array_val
      FROM archive.sample s
      JOIN archive.channel c ON c.channel_id = s.channel_id
    
     WHERE s.channel_id in (
            SELECT channel_id
              FROM archive.channel c
             WHERE name in ({0}))
            
	   AND s.smpl_time > %s
       AND s.smpl_time <= %s
"""


class ArchiverDataSource(object):

    def __init__(self, pv_names, start_time, period, point_count, sql_abstraction_layer):

        self._end_time = start_time + period * point_count
        self._sql_abstraction_layer = sql_abstraction_layer
        self._start_time = start_time
        self._pv_names = pv_names
        self._initial_pv_details = None

    def initial_values(self):
        """
        :return: initial values for the pvs (i.e. the value at the start time)
        """
        initial_values = []
        for pv_name in self._pv_names:
            result = self._sql_abstraction_layer.query(INITIAL_VALUES_QUERY, (pv_name, self._start_time))
            if len(result) == 1:
                initial_values.append(ArchiverDataValue(result[0]).value)
            elif len(result) == 0:
                initial_values.append(None)
            else:
                initial_values.append(VALUE_WHEN_ERROR_ON_RETRIEVAL)

        return initial_values

    def changes_generator(self):
        query_with_correct_number_of_bound_ins = GET_CHANGES_QUERY.format(", ".join(["%s"] * len(self._pv_names)))
        for database_return in self._sql_abstraction_layer.query_returning_cursor(query_with_correct_number_of_bound_ins, self._pv_names + (self._start_time, self._end_time)):
            value = ArchiverDataValue(database_return[2:])
            channel_name = database_return[0]
            index = self._pv_names.index(channel_name)
            time_stamp = database_return[1]
            yield(time_stamp, index, value.value)

if __name__ == "__main__":
    ads = ArchiverDataSource(('TE:NDW1798:TPG26X_01:2:ERROR.VAL', 'TE:NDW1798:EUROTHRM_01:A01:TEMP.VAL'),
                             datetime(2020, 06, 16, 0, 0, 0),
                             timedelta(days=365),
                             10,
                            SQLAbstraction("archive", "report", "$report"))
    for val in ads.initial_values():
        print str(val)

    for val in ads.changes_generator():
        print str(val)
