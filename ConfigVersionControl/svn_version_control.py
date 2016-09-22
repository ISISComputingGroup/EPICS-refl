# Version Control class for dealing with SVN file operations
from vc_exceptions import NotUnderVersionControl
import subprocess
import os


class SVNVersionControl:

    def __init__(self, working_directory):
        #check that supplied directory is under version control
        try:
            self.info(working_directory)
        except subprocess.CalledProcessError:
            raise NotUnderVersionControl(working_directory)

    # TODO: Waits with no timeout here!!
    @staticmethod
    def info(self, working_directory):
        # returns some information on the repository
        subprocess.check_call(["svn", "info", working_directory], stdout=subprocess.PIPE)

    @staticmethod
    def add(self, path):
        # adds a file to the repository
        pro = subprocess.Popen("svn add \"" + path + "\"", stdout=subprocess.PIPE)
        pro.wait()

    @staticmethod
    def commit(self, working_directory, commit_comment):
        # commits changes to a file to the repository

        curr_dir = os.getcwd()
        os.chdir(working_directory)

        pro = subprocess.Popen("svn commit -m \"" + commit_comment + "\"", stdout=subprocess.PIPE)
        pro.wait()
        os.chdir(curr_dir)

    @staticmethod
    def update(self, update_path):
        # updates local copy from the repository
        curr_dir = os.getcwd()
        os.chdir(update_path)
        p = subprocess.Popen("svn update", stdout=subprocess.PIPE)
        p.wait()
        os.chdir(curr_dir)

    @staticmethod
    def remove(self, path):
        pro = subprocess.Popen("svn delete \"" + path + "\"", stdout=subprocess.PIPE)
        pro.wait()