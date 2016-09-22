from version_control_wrapper import VersionControlWrapper
from constants import *


class ConfigVersionControl:

    def __init__(self, working_directory):
        self.working_directory = working_directory
        self.version_control = VersionControlWrapper(working_directory, GIT_TYPE)

    #i.e. not automatically via the file observer firing an event, but after a new configuration is created
    #or an existing one updated via the GUI.
    def add(self, file_path):
        self.version_control.add(file_path)

    def remove(self, file_path):
        self.version_control.remove(file_path)

    #and supply a message for the commit (e.g. change to configuration)
    #i.e. not automatically as explained above
    def commit(self, commit_comment):
        self.version_control.commit(commit_comment)

    def update(self, update_path=""):
        if update_path == "":
            update_path = self.working_directory
        self.version_control.update(update_path)

if __name__ == "__main__":
    path = "C:\Instrument\Settings\config\\test_git\\test"
    test = ConfigVersionControl(path)
    while 1:
        pass
