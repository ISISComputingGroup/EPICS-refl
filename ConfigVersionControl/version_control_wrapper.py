# Abstraction class to sit between main and Version Control System
from svn_version_control import SVNVersionControl
from git_version_control import GitVersionControl
from constants import *


class VersionControlWrapper:

    def __init__(self, working_directory, vc_type):
        self.working_directory = working_directory
        if vc_type == SVN_TYPE:
            self.implements = SVNVersionControl(working_directory)
        elif vc_type == GIT_TYPE:
            self.implements = GitVersionControl(working_directory)

    def info(self, path):
        # return some information on the repository
        self.implements.info(path)

    def add(self, path):
        # add file to repository
        self.implements.add(path)

    def commit(self, commit_comment="Default Comment - Changed File"):
        # commit changes to repository
        # SVN (and possibly GIT) requires a comment for each commit.
        self.implements.commit(self.working_directory, commit_comment)

    def update(self, update_path):
        # update local file from repository
        self.implements.update(update_path)

    def remove(self, path):
        self.implements.remove(path)
