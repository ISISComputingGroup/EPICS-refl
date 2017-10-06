import os

from BlockServer.core.file_path_manager import FILEPATH_MANAGER

CONFIG_DIR = "configurations\\configurations\\"
COMP_DIR = "configurations\\components\\"
SYNOPTIC_DIR = "configurations\\synoptics\\"
DEVICES_DIR = "configurations\\devices\\"


class CommitMessageProvider:

    def __init__(self):
        self._reset()

    @staticmethod
    def _is_config(path):
        return CONFIG_DIR in path

    @staticmethod
    def _is_component(path):
        return COMP_DIR in path

    @staticmethod
    def _is_synoptic(path):
        return SYNOPTIC_DIR in path and path.endswith(".xml")

    @staticmethod
    def _is_device_screens(path):
        return DEVICES_DIR in path and path.endswith("screens.xml")

    @staticmethod
    def _is_script(path):
        return FILEPATH_MANAGER.scripts_dir in path and path.endswith(".py")

    @staticmethod
    def _append(msg, to_append):
        if len(msg) > 0:
            msg += ", "
        msg += to_append

        return msg

    def get_commit_message(self, diff):
        for item in diff:
            path = os.path.normcase(item.a_rawpath)
            path = os.path.normpath(path)
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
        self._scripts_deleted |= self._is_script(path)

    def _assemble_message(self):
        message = ""

        if self._configs_modified:
            message = self._append(message, "Configurations modified")
        if self._configs_deleted:
            message = self._append(message, "Configurations deleted")
        if self._comps_modified:
            message = self._append(message, "Components modified")
        if self._comps_deleted:
            message = self._append(message, "Components deleted")
        if self._synoptics_modified:
            message = self._append(message, "Synoptics modified")
        if self._synoptics_deleted:
            message = self._append(message, "Synoptics deleted")
        if self._device_screens_modified:
            message = self._append(message, "Device screens modified")
        if self._scripts_modified:
            message = self._append(message, "Scripts modified")
        if self._scripts_deleted:
            message = self._append(message, "Scripts deleted")
        if self._scripts_modified:
            message = self._append(message, "Other files modified")
            
        self._reset()

        return message


    def _reset(self):
        self._configs_modified = False
        self._configs_deleted = False

        self._comps_modified = False
        self._comps_deleted = False

        self._synoptics_modified = False
        self._synoptics_deleted = False

        self._scripts_modified = False
        self._scripts_deleted = False

        self._device_screens_modified = False

        self._other_modified = False
