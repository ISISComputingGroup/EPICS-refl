from server_common.utilities import compress_and_hex
from BlockServer.core.file_path_manager import FILEPATH_MANAGER

GET_SCREENS = "GET_SCREENS"
SET_SCREENS = "SET_SCREENS"

TEST_DATA = """<?xml version="1.0" ?>
<devices xmlns:xi="http://www.w3.org/2001/XInclude">
    <device>
        <name>Eurotherm 1</name>
        <key>Eurotherm</key>
        <type>OPI</type>
        <properties>
            <property>
                <key>EURO</key>
                <value>EUROTHERM1</value>
            </property>
        </properties>
    </device>
</devices>"""


class DevicesManager(object):
    """Class for managing the PVs associated with devices"""
    def __init__(self, block_server, cas, schema_folder, vc_manager):
        """Constructor.

        Args:
            block_server (BlockServer): A reference to the BlockServer instance.
            cas (CAServer): The channel access server for creating PVs on-the-fly
            schema_folder (string): The filepath for the devices schema
            vc_manager (ConfigVersionControl): The manager to allow version control modifications
        """
        self._directory = FILEPATH_MANAGER.config_dir
        self._schema_folder = schema_folder
        self._cas = cas
        self._devices_pvs = dict()
        self._vc = vc_manager
        self._bs = block_server
        self._default_dev_xml = ""
        self._create_pv(TEST_DATA)


    def _create_pv(self, data):
        """Creates a single PV based on a name and data.

        Args:
            data (string): Starting data for the pv, the pv name is derived from the name tag of this
        """

        # Create the PV
        self._cas.updatePV(GET_SCREENS, compress_and_hex(data))