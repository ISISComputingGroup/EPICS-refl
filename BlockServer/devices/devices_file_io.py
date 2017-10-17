import os
from server_common.utilities import print_and_log, retry
from xml.dom import minidom

RETRY_MAX_ATTEMPTS = 20
RETRY_INTERVAL = 0.5


class DevicesFileIO(object):
    """Responsible for loading and saving the devices file."""

    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, IOError)
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

        with open(file_name, 'r') as devfile:
            data = devfile.read()
            return data

    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, IOError)
    def save_devices_file(self, file_name, data):
        """Saves the devices info.

        Args:
            file_name (string): the devices file (full path)
            data (string): the xml to save
        """
        # If save file already exists remove first to avoid case issues
        if os.path.exists(file_name):
            os.remove(file_name)

        # Save the data
        with open(file_name, 'w') as devfile:
            pretty_xml = minidom.parseString(data).toprettyxml()
            devfile.write(pretty_xml)
