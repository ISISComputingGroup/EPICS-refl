import os

CONFIG_DIR = os.path.join("configurations", "configurations")
COMP_DIR = os.path.join("configurations", "components")
SYNOPTIC_DIR = os.path.join("configurations", "synoptics")
DEVICES_DIR = os.path.join("configurations", "devices")
SCRIPTS_DIR = os.path.join("python", "")


class GitMessageProvider:

    CONFIGS_MODIFIED = "Configurations modified"
    CONFIGS_DELETED = "Configurations deleted"
    COMPS_MODIFIED = "Components modified"
    COMPS_DELETED = "Components deleted"
    SYN_MODIFIED = "Synoptics modified"
    SYN_DELETED = "Synoptics deleted"
    SCRIPTS_MODIFIED = "Scripts modified"
    SCRIPTS_DELETED = "Scripts deleted"
    DEVICES_MODIFIED = "Device screens modified"
    DEVICES_DELETED = "Device screens deleted"
    OTHER_MODIFIED = "Other files modified"

    def __init__(self):
        self._reset()

    @staticmethod
    def _is_config(path):
        return CONFIG_DIR in path and path.endswith(".xml")

    @staticmethod
    def _is_component(path):
        return COMP_DIR in path and path.endswith(".xml")

    @staticmethod
    def _is_synoptic(path):
        return SYNOPTIC_DIR in path and path.endswith(".xml")

    @staticmethod
    def _is_device_screens(path):
        return DEVICES_DIR in path and path.endswith("screens.xml")

    @staticmethod
    def _is_script(path):
        return SCRIPTS_DIR in path and path.endswith(".py")

    @staticmethod
    def _append(msg, to_append):
        if len(msg) > 0:
            msg += ", "
        msg += to_append

        return msg

    def get_commit_message(self, diff):
        for item in diff:
            # First line of diff item contains file path
            path = str(item).split("\n")[0]
            path = os.path.normcase(os.path.normpath(path))
            if item.new_file:  # For some reason this is true when file deleted
                self._deleted(path)
            else:
                self._modified(path)

        return self._assemble_message()

    def _modified(self, path):
        self._configs_modified |= self._is_config(path)
        self._comps_modified |= self._is_component(path)
        self._synoptics_modified |= self._is_synoptic(path)
        self._device_screens_modified |= self._is_device_screens(path)
        self._scripts_modified |= self._is_script(path)
        self._other_modified |= not (self._is_config(path) or self._is_component(path) or self._is_synoptic(path) or
                                     self._is_device_screens(path) or self._is_script(path))

    def _deleted(self, path):
        self._configs_deleted |= self._is_config(path)
        self._comps_deleted |= self._is_component(path)
        self._synoptics_deleted |= self._is_synoptic(path)
        self._device_screens_deleted |= self._is_device_screens(path)
        self._scripts_deleted |= self._is_script(path)
        self._other_modified |= not (self._is_config(path) or self._is_component(path) or self._is_synoptic(path) or
                                     self._is_device_screens(path) or self._is_script(path))

    def _assemble_message(self):
        message = ""

        if self._configs_modified:
            message = self._append(message, self.CONFIGS_MODIFIED)
        if self._configs_deleted:
            message = self._append(message, self.CONFIGS_DELETED)
        if self._comps_modified:
            message = self._append(message, self.COMPS_MODIFIED)
        if self._comps_deleted:
            message = self._append(message, self.COMPS_DELETED)
        if self._synoptics_modified:
            message = self._append(message, self.SYN_MODIFIED)
        if self._synoptics_deleted:
            message = self._append(message, self.SYN_DELETED)
        if self._device_screens_modified:
            message = self._append(message, self.DEVICES_MODIFIED)
        if self._device_screens_deleted:
            message = self._append(message, self.DEVICES_DELETED)
        if self._scripts_modified:
            message = self._append(message, self.SCRIPTS_MODIFIED)
        if self._scripts_deleted:
            message = self._append(message, self.SCRIPTS_DELETED)
        if self._other_modified:
            message = self._append(message, self.OTHER_MODIFIED)
            
        self._reset()

        return message

    def _reset(self):
        self._configs_modified = False
        self._configs_deleted = False

        self._comps_modified = False
        self._comps_deleted = False

        self._synoptics_modified = False
        self._synoptics_deleted = False

        self._device_screens_modified = False
        self._device_screens_deleted = False

        self._scripts_modified = False
        self._scripts_deleted = False

        self._other_modified = False
