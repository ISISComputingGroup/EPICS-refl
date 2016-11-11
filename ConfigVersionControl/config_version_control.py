import os
import shutil
from version_control_wrapper import VersionControlWrapper
from constants import *

+SYSTEM_TEST_PREFIX = "rcptt_"


class ConfigVersionControl:

    def __init__(self, working_directory):
        self.working_directory = working_directory
        self.version_control = VersionControlWrapper(working_directory, GIT_TYPE)

    #i.e. not automatically via the file observer firing an event, but after a new configuration is created
    #or an existing one updated via the GUI.
    def add(self, file_path):
        if self._should_ignore(file_path):
            return
        self.version_control.add(file_path)

    def remove(self, file_path):
        if self._should_ignore(file_path) and os.path.exists(file_path):
            # the git library throws if we try to delete something that wasn't added
            # but we still have to delete the file from file system
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            return

        self.version_control.remove(file_path)

    #and supply a message for the commit (e.g. change to configuration)
    #i.e. not automatically as explained above
    def commit(self, commit_comment):
        self.version_control.commit(commit_comment)

    def update(self, update_path=""):
        if update_path == "":
            update_path = self.working_directory
        self.version_control.update(update_path)

    def _should_ignore(self, file_path):
        # Ignore anything that starts with the system tests prefix
        # (unfortunately putting the system test prefix in the .gitignore doesn't work
        # because the git library always forces an add - it has a force flag, but it's not used)
        return SYSTEM_TEST_PREFIX in file_path

if __name__ == "__main__":
    path = "C:\Instrument\Settings\config\\test_git\\test"
    test = ConfigVersionControl(path)
    while 1:
        pass
