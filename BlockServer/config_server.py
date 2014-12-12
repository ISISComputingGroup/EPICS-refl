import os
import json
from archiver_manager import ArchiverManager
from config.constants import AUTOSAVE_NAME, IOCS_NOT_TO_STOP, RUNCONTROL_IOC, RUNCONTROL_SETTINGS, CONFIG_DIRECTORY, \
    COMPONENT_DIRECTORY
from procserv_utils import ProcServWrapper
from runcontrol import RunControlManager
from utilities import print_and_log
from config.json_converter import ConfigurationJsonConverter
from config_holder import ConfigHolder
from database_server_client import DatabaseServerClient
from macros import BLOCKSERVER_PREFIX


class ConfigServerManager(object):
    # TODO: Inherit from inactive?
    def __init__(self, config_folder, macros, archive_uploader, archive_config, block_prefix, test_mode=False):
        self._config_folder = config_folder
        self._macros = macros
        self._archive_manager = ArchiverManager(archive_uploader, archive_config)
        self._procserve_wrapper = ProcServWrapper()
        self._block_prefix = block_prefix
        self._db = None
        self._last_config_file = os.path.abspath(config_folder + "/last_config.txt")
        self._runcontrol = RunControlManager(self._macros["$(MYPVPREFIX)"],
                                             self._macros["$(ICPCONFIGROOT)"] + RUNCONTROL_SETTINGS)

        self._config_holder = ConfigHolder(self._config_folder,  self._macros)
        self._db_client = DatabaseServerClient(BLOCKSERVER_PREFIX)

        if not test_mode:
            # Start runcontrol IOC
            try:
                self._procserve_wrapper.start_ioc(self._macros["$(MYPVPREFIX)"], RUNCONTROL_IOC)
            except Exception as err:
                print_and_log("Problem with starting the run-control IOC: %s" % err)
            # Need to wait for RUNCONTROL_IOC to (re)start
            print_and_log("Waiting for runcontrol IOC to (re)start")
            self._runcontrol.wait_for_ioc_start()
            print_and_log("Runcontrol IOC (re)started")

        self._conf_path = os.path.abspath(self._config_folder + CONFIG_DIRECTORY)
        self._comp_path = os.path.abspath(self._config_folder + COMPONENT_DIRECTORY)

        if test_mode:
            self._set_testing_mode()

    def _set_testing_mode(self):
        self._archive_manager.set_testing_mode(True)
        from mocks.mock_procserv_utils import MockProcServWrapper
        self._procserve_wrapper = MockProcServWrapper()
        from mocks.mock_runcontrol import MockRunControlManager
        self._runcontrol = MockRunControlManager()

    def add_blocks_json(self, input):
        if input is None:
            raise Exception("Failed to add block as no parameters were supplied")
        data = json.loads(input)
        for blk in data:
            self._config_holder.add_block(blk)

    def remove_blocks(self, input):
        data = json.loads(input)
        for blk in data:
            self._config_holder.remove_block(blk)
        self.create_runcontrol_pvs()

    def get_blocks(self):
        return self._config_holder.get_block_details()

    def edit_blocks_json(self, input):
        data = json.loads(input)
        for blk in data:
            self._config_holder.edit_block(blk)
        self.create_runcontrol_pvs()

    def get_blocknames_json(self):
        block_names = json.dumps(self._config_holder.get_blocknames())
        return block_names.encode('ascii', 'replace')

    def get_groupings_json(self):
        output = ConfigurationJsonConverter.groups_to_json(self._config_holder.get_group_details())
        return output.encode('ascii', 'replace')

    def set_groupings_json(self, data):
        grps = ConfigurationJsonConverter.groups_from_json(data)
        self._config_holder.set_group_details(grps)

    def get_config_iocs_json(self):
        return json.dumps(self._config_holder.get_ioc_names()).encode('ascii', 'replace')

    def clear_config(self):
        self._config_holder.clear_config()

    def get_config_name_json(self):
        config = self._config_holder.get_config_name()
        return json.dumps(config).encode('ascii', 'replace')

    def add_iocs(self, input):
        data = json.loads(input)
        for ioc in data:
            self._add_ioc(ioc)

    def _add_ioc(self, iocname, start=False):
        if self._procserve_wrapper.ioc_exists(self._macros["$(MYPVPREFIX)"], iocname):
            self._config_holder.add_ioc(iocname)
            if start:
                self._start_ioc(iocname)
        else:
            raise Exception("Could not start IOC %s as it does not exist" % iocname)

    def remove_iocs(self, input):
        data = json.loads(input)
        for ioc in data:
            self._remove_ioc(ioc)

    def _remove_ioc(self, iocname):
        self._config_holder.remove_ioc(iocname)

    def _get_config_iocs_names(self):
        return self._config_holder.get_ioc_names()

    def _get_config_iocs_details(self):
        return self._config_holder.get_ioc_details()

    def save_config(self, input):
        # The config name comes as JSON
        conf = json.loads(input)
        self._save_config(conf)

    def _save_config(self, name):
        if self._config_holder.is_subconfig():
            self._config_holder.save_config(name)
            self.set_last_config(COMPONENT_DIRECTORY + name)
        else:
            self._config_holder.update_runcontrol_settings_for_saving(self._get_runcontrol_settings())
            self._config_holder.save_config(name)
            self.set_last_config(CONFIG_DIRECTORY + name)

    def save_as_subconfig(self, name):
        conf = json.loads(name)
        self._config_holder.set_as_subconfig(True)
        self._config_holder.save_config(conf)
        self.set_last_config(COMPONENT_DIRECTORY + conf)

    def autosave_config(self):
        self._save_config(AUTOSAVE_NAME)

    def load_config(self, name, is_subconfig=False):
        # The config name comes as JSON
        conf = json.loads(name)
        self._load_config(conf, is_subconfig)

    def _load_config(self, name, is_subconfig=False):
        if is_subconfig:
            comp = self._config_holder.load_config(name, True)
            self._config_holder.set_config(comp, True)
            self.set_last_config(COMPONENT_DIRECTORY + name)
        else:
            conf = self._config_holder.load_config(name, False)
            self._config_holder.set_config(conf, False)
            self.set_last_config(CONFIG_DIRECTORY + name)
        self.create_runcontrol_pvs()
        self._runcontrol.restore_config_settings(self._config_holder.get_block_details())

    def get_ioc_state(self, ioc):
        return self._procserve_wrapper.get_ioc_status(self._macros["$(MYPVPREFIX)"], ioc)

    def start_iocs(self, input):
        data = json.loads(input)
        for ioc in data:
            self._start_ioc(ioc)

    def _start_ioc(self, ioc):
        self._procserve_wrapper.start_ioc(self._macros["$(MYPVPREFIX)"], ioc)

    def _start_config_iocs(self):
        # Start the IOCs, if they are available and if they are flagged for autostart
        for n, ioc in self._get_config_iocs_details().iteritems():
            try:
                # Throws if IOC does not exist
                # If it is already running restart it, otherwise start it
                running = self.get_ioc_state(n)
                if running == "RUNNING":
                    if ioc.restart:
                        self._restart_ioc(n)
                else:
                    if ioc.autostart:
                        self._start_ioc(n)
            except Exception as err:
                print_and_log("Could not (re)start IOC %s: %s" % (n, str(err)))

    def restart_iocs(self, input):
        data = json.loads(input)
        for ioc in data:
            self._restart_ioc(ioc)

    def _restart_ioc(self, ioc):
        self._procserve_wrapper.restart_ioc(self._macros["$(MYPVPREFIX)"], ioc)

    def stop_iocs(self, input):
        data = json.loads(input)
        for ioc in data:
            # Check it is okay to stop it
            if ioc.startswith(IOCS_NOT_TO_STOP):
                continue
            self._stop_ioc(ioc)

    def _stop_ioc(self, ioc):
        self._procserve_wrapper.stop_ioc(self._macros["$(MYPVPREFIX)"], ioc)

    def stop_config_iocs(self):
        iocs = self._config_holder.get_ioc_names()
        self._stop_iocs(iocs)

    def stop_iocs_and_start_config_iocs(self):
        non_conf_iocs = [x for x in self._get_iocs() if x not in self._get_config_iocs_names()]
        self._stop_iocs(non_conf_iocs)
        self._start_config_iocs()

    def _stop_iocs(self, iocs):
        iocs_to_stop = [x for x in iocs if not x.startswith(IOCS_NOT_TO_STOP)]
        for n in iocs_to_stop:
            try:
                # Throws if IOC does not exist
                running = self.get_ioc_state(n)
                if running == "RUNNING":
                    self._stop_ioc(n)
            except Exception as err:
                print_and_log("Could not stop IOC %s: %s" % (n, str(err)))

    def get_config_folder(self):
        return self._config_folder

    def get_configs(self):
        config_folder = os.path.abspath(self._conf_path)
        configs = []
        if os.path.isdir(config_folder):
            configs = [f for f in os.listdir(config_folder) if os.path.isdir(os.path.join(config_folder, f))]
        return configs

    def get_configs_json(self):
        return json.dumps(self.get_configs()).encode('ascii', 'replace')

    def get_subconfigs(self):
        """Returns a list of the available sub-configurations"""
        config_folder = os.path.abspath(self._comp_path)
        configs = []
        if os.path.isdir(config_folder):
            configs = [f for f in os.listdir(config_folder) if os.path.isdir(os.path.join(config_folder, f))]
        return configs

    def get_subconfigs_json(self):
        return json.dumps(self.get_subconfigs()).encode('ascii', 'replace')

    def get_block_prefix_json(self):
        return json.dumps(self._macros["$(MYPVPREFIX)"] + self._block_prefix).encode('ascii', 'replace')

    def update_archiver(self):
        self._archive_manager.update_archiver(self.get_block_prefix_json(), self._config_holder.get_blocknames())

    def _get_iocs(self, include_running=False):
        # Get IOCs from DatabaseServer
        try:
            return self._db_client.get_iocs()
        except Exception as err:
            print_and_log("Could not retrieve IOC list: %s" % str(err), "ERROR")
            return []

    def add_subconfigs(self, input):
        data = json.loads(input)
        for name in data:
            comp = self._config_holder.load_config(name, True)
            self._config_holder.add_subconfig(name, comp)
            # Load any IOCs for that subconfig
            for n, ioc in comp.iocs.iteritems():
                if self.get_ioc_state(ioc.name) == "SHUTDOWN":
                    self._start_ioc(ioc.name)

    def remove_subconfigs(self, input):
        data = json.loads(input)
        for name in data:
            self._config_holder.remove_subconfig(name)

    def get_conf_subconfigs_json(self):
        """Gets a list of sub-configurations in the current config"""
        return json.dumps(self._config_holder.get_component_names()).encode('ascii', 'replace')

    def set_last_config(self, config):
        last = os.path.abspath(self._last_config_file)
        with open(last, 'w') as f:
            f.write(config + "\n")

    def load_last_config(self):
        last = os.path.abspath(self._last_config_file)
        if not os.path.isfile(last):
            return None
        with open(last, 'r') as f:
            last_config = f.readline().strip()
        if last_config.replace(COMPONENT_DIRECTORY, "").replace(CONFIG_DIRECTORY, "").strip() == "":
            print_and_log("No last configuration defined")
            return None
        print_and_log("Trying to load last_configuration %s" % last_config)
        if last_config.startswith(COMPONENT_DIRECTORY):
            self._load_config(last_config.replace(COMPONENT_DIRECTORY, ""), True)
        else:
            self._load_config(last_config.replace(CONFIG_DIRECTORY, ""), False)
        return last_config

    def dump_status(self):
        data = self._config_holder.dump_status()
        f = open(self._config_folder + '/blockserver_status.txt', 'w')
        f.write(data)
        f.close()

    def create_runcontrol_pvs(self):
        self._runcontrol.update_runcontrol_blocks(self._config_holder.get_block_details())
        self._procserve_wrapper.restart_ioc(self._macros["$(MYPVPREFIX)"], RUNCONTROL_IOC)
        # Need to wait for RUNCONTROL_IOC to restart
        self._runcontrol.wait_for_ioc_start()

    def get_out_of_range_pvs(self):
        return json.dumps(self._runcontrol.get_out_of_range_pvs()).encode('ascii', 'replace')

    def get_runcontrol_settings_json(self):
        return json.dumps(self._get_runcontrol_settings()).encode('ascii', 'replace')

    def _get_runcontrol_settings(self):
        return self._runcontrol.get_runcontrol_settings(self._config_holder.get_block_details())

    def set_runcontrol_settings_json(self, data):
        self._runcontrol.set_runcontrol_settings(json.loads(data))

    def get_config_details(self):
        js = json.dumps(self._config_holder.get_config_details())
        return js.encode('ascii', 'replace')

    def set_config_details(self, data):
        self._config_holder.set_config_details_from_json(json.loads(data))

