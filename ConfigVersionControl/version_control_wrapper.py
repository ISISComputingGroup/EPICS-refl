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
        """ Get some info on the repository
        Args:
            path (str): the path to the repository

        Returns:
            string: Info about the repository
        """
        self.implements.info(path)

    def add(self, path):
        """ Add a file to the repository
        Args:
            path (str): the file to add
        """
        self.implements.add(path)

    def commit(self, commit_comment="Default Comment - Changed File"):
        """ Commit changes to a repository
        Args:
            commit_comment (str): comment to leave with the commit
        """
        self.implements.commit(self.working_directory, commit_comment)

    def update(self, update_path):
        # update local file from repository
        self.implements.update(update_path)

    def remove(self, path):
        self.implements.remove(path)
