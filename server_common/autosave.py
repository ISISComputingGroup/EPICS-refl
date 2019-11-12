from __future__ import unicode_literals, print_function, division, absolute_import

import os
import threading

import six

from server_common.utilities import print_and_log

ICP_VAR_DIR = os.path.normpath(os.environ.get("ICPVARDIR", os.path.join("C:\\", "Instrument", "var")))


class AutosaveFile(object):
    """
    An Autosave object useful for saving values that can be read and written at sensible points in time.
    """

    def __init__(self, service_name, file_name, folder=None):
        """
        Creates a new AutosaveFile object.

        Args:
            service_name: The name of the service that is autosaving this parameter, e.g. BlockServer or RemoteIocServer
            file_name: The name of the specific autosave file to create, e.g. "positions" or "settings"
        """
        self._folder = folder if folder is not None else os.path.join(ICP_VAR_DIR, service_name)

        self._filepath = os.path.join(self._folder, "{}.txt".format(file_name))

        # Prevents multiple threads from conflicting when reading/writing the same autosave file.
        # Note: does not prevent two different AutosaveFile objects from pointing at the same path.
        self._file_lock = threading.RLock()

        self.autosave_separator = " "

    def write_parameter(self, parameter, value):
        """
        Writes a parameter to the autosave file.

        Args:
            parameter: The unique name for the parameter which is being autosaved
            value: the value to save.
        """
        if self.autosave_separator in parameter:
            # Disallow embedding the separator inside the value as this will cause a read to fail later.
            raise ValueError("Parameter name '{}' contains autosave separator which is not allowed".format(parameter))

        if "\n" in str(value) or "\n" in parameter:
            # Autosave parameters are saved one-per-line, newlines would interfere with this.
            raise ValueError("Value or parameter contains line separator which is now allowed")

        with self._file_lock:
            saved_parameters = self._file_to_dict()
            saved_parameters[parameter] = value
            self._dict_to_file(saved_parameters)

    def read_parameter(self, parameter, default):
        """
        Reads a parameter from the autosave file.

        Args:
            parameter: The unique name for the parameter which is being read
            default: The value to return if the requested parameter does not have an autosaved value
        """
        with self._file_lock:
            return self._file_to_dict().get(parameter, default)

    def _file_to_dict(self):
        """
        Gets a dictionary of autosaved parameters from an autosave file.

        Returns:
            the dictionary in the format parameter_name: autosaved_value
        """
        parameters = {}
        try:
            for line in self._autosave_file_lines():
                try:
                    p, v = line.split(self.autosave_separator, 1)
                    parameters[p] = v.strip()
                except ValueError:
                    print_and_log("ValueError when reading autosave file, ignoring line: '{}'".format(line))
        except (IOError, ValueError) as e:
            print_and_log("Error while reading autosave file at '{}': {}: {}"
                          .format(self._filepath, e.__class__.__name__, e))
        return parameters

    def _dict_to_file(self, parameters):
        """
        Saves a dictionary in the format parameter_name: autosaved_value to file

        Args:
             parameters: the dictionary of *all* parameters in the format parameter_name: value
        """
        if not os.path.exists(self._folder):
            os.makedirs(self._folder)

        file_content = "\n".join("{}{}{}".format(param, self.autosave_separator, value)
                                                for param, value in six.iteritems(parameters))
        with self._file_lock, open(self._filepath, "w+") as f:
            return f.write(file_content)

    def _autosave_file_lines(self):
        with self._file_lock, open(self._filepath) as f:
            return f.readlines()
