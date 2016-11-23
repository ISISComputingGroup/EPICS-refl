import os
import shutil
from constants import *
from git_version_control import GitVersionControl

SYSTEM_TEST_PREFIX = "rcptt_"


class ConfigVersionControl:

    def __init__(self, working_directory, version_control=None):
        self.working_directory = working_directory
        if version_control is None:
            self.version_control = GitVersionControl(working_directory)
        else:
            self.version_control = version_control

    def add(self, file_path):
        """ Add a file to the repository
        Args:
            path (str): the file to add
        """
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

    def commit(self, commit_comment):
        """ Commit changes to a repository
        Args:
            commit_comment (str): comment to leave with the commit
        """
        self.version_control.commit(commit_comment)

    def update(self):
        self.version_control.update()

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
