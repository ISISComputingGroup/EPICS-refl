import os
from xml.dom import minidom
from BlockServer.fileIO.schema_checker import ConfigurationSchemaChecker


class DevicesFileIO(object):
    """Responsible for loading and saving the devices file."""

    def load_devices_file(self, file_name):
        """Load the devices file.

        Args:
            file_name (string): the devices file (full path)

        Returns:
            string: the XML as a string
        """
        with open(file_name, 'r') as devfile:
            data = devfile.read()

        return data

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
