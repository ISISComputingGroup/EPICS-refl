import os

_CONFIG_DIRECTORY = "configurations"
_COMPONENT_DIRECTORY = "components"
_SYNOPTIC_DIRECTORY = "synoptics"


# Do not create an instance of this class, instead use FILEPATH_MANAGER as a singleton
class FilePathManager(object):
    def __init__(self):
        self.config_root_dir = ""
        self.config_dir = ""
        self.component_dir = ""
        self.synoptic_dir = ""

    def initialise(self, config_root):
        self.config_root_dir = config_root
        self.config_dir = os.path.join(config_root, _CONFIG_DIRECTORY)
        self.component_dir = os.path.join(config_root, _COMPONENT_DIRECTORY)
        self.synoptic_dir = os.path.join(config_root, _SYNOPTIC_DIRECTORY)
        self._create_default_folders()

    def _create_default_folders(self):
        # Create default folders
        paths = [self.config_root_dir, self.config_dir, self.component_dir, self.synoptic_dir]
        for p in paths:
            if not os.path.isdir(p):
                # Create it then
                os.makedirs(os.path.abspath(p))

# This is the singleton to use
FILEPATH_MANAGER = FilePathManager()
