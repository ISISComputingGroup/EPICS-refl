import os

CONFIG_DIRECTORY = "configurations"
COMPONENT_DIRECTORY = "components"
SYNOPTIC_DIRECTORY = "synoptics"


# Do not create an instance of this class, instead use FILEPATH_MANAGER as a singleton
class FilePathManager(object):
    def __init__(self):
        self.config_root_dir = ""
        self.config_dir = ""
        self.component_dir = ""
        self.synoptic_dir = ""

    def initialise(self, config_root):
        self.config_root_dir = config_root
        self.config_dir = os.path.join(config_root, CONFIG_DIRECTORY)
        self.component_dir = os.path.join(config_root, COMPONENT_DIRECTORY)
        self.synoptic_dir = os.path.join(config_root, SYNOPTIC_DIRECTORY)
        self._create_default_folders()

    def _create_default_folders(self):
        # Create default folders
        paths = [self.config_root_dir, self.config_dir, self.component_dir, self.synoptic_dir]
        for p in paths:
            if not os.path.isdir(p):
                # Create it then
                os.makedirs(os.path.abspath(p))

    def get_component_path(self, component_name):
        return os.path.join(self.component_dir, component_name) + os.sep

    def get_config_path(self, config_name):
        return os.path.join(self.config_dir, config_name) + os.sep

    def get_synoptic_path(self, synoptic_name):
        return os.path.join(self.synoptic_dir, synoptic_name) + ".xml"

# This is the singleton to use
FILEPATH_MANAGER = FilePathManager()
