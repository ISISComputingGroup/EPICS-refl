from __future__ import print_function, absolute_import, division, unicode_literals
import json
from server_common.utilities import compress_and_hex


class MockExpData(object):
    def encode_for_return(self, data):
        return compress_and_hex(json.dumps(data).encode('utf-8', 'replace'))

    def _get_surname_from_fullname(self, fullname):
        try:
            return fullname.split(" ")[-1]
        except:
            return fullname

    def update_experiment_id(self, experiment_id):
        """
        Updates the associated PVs when an experiment ID is set.

        Args:
            experiment_id (string): the id of the experiment to load related data from

        Returns:
            None specifically, but the following information external to the server is set
            # TODO: Update with the correct PVs for this part

        """
        pass

    def update_username(self, users):
        pass

    @staticmethod
    def make_name_list_ascii(names):
        pass
