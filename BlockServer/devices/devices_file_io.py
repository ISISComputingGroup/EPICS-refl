import os
import time
from server_common.utilities import print_and_log
from xml.dom import minidom

RETRY_MAX_ATTEMPTS = 30
RETRY_INTERVAL = 1


class DevicesFileIO(object):
    """Responsible for loading and saving the devices file."""

    def load_devices_file(self, file_name):
        """Load the devices file.

        Args:
            file_name (string): the devices file (full path)

        Returns:
            string: the XML as a string
        """

        # Create the file if it does not exist
        if not os.path.exists(file_name):
            print_and_log("Device screens file not found.")
            return ""

        attempts = 0
        while attempts < RETRY_MAX_ATTEMPTS:
            try:

                with open(file_name, 'r') as devfile:
                    data = devfile.read()
                    return data

            except IOError:
                attempts += 1
                time.sleep(RETRY_INTERVAL)

        raise Exception(
            "Could not load device screens file at %s. Please check the file is not in use by another process." % file_name)

    def save_devices_file(self, file_name, data):
        """Saves the devices info.

        Args:
            file_name (string): the devices file (full path)
            data (string): the xml to save
        """
        attempts = 0
        while attempts < RETRY_MAX_ATTEMPTS:
            try:
                # If save file already exists remove first to avoid case issues
                if os.path.exists(file_name):
                    os.remove(file_name)
                # Save the data
                with open(file_name, 'w') as devfile:
                    pretty_xml = minidom.parseString(data).toprettyxml()
                    devfile.write(pretty_xml)
                    return

            except IOError:
                attempts += 1
                time.sleep(RETRY_INTERVAL)

        raise Exception(
            "Could not save to device screens file at %s. Please check the file is not in use by another process." % file_name)
