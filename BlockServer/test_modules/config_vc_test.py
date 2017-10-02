import os
import shutil
import unittest

from watchdog.events import *
from ConfigVersionControl.git_version_control import GitVersionControl
from git import Repo

TEST_DIR = os.path.abspath(os.path.join(__file__, "..", "test_git"))


def clean_up():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)


def create_dummy_file(repo):
    # Creates a dummy file in the repository as GitPython will not allow creating a new branch in a blank repository.
    # This is necessary as the default master branch is disallowed by the version control manager under test.
    filename = os.path.join(TEST_DIR, 'dummy.txt')
    open(filename, 'wb').close()
    repo.index.add([filename])
    repo.index.commit("Initialising repository with file " + filename)


class TestConfigFileEventHandler(unittest.TestCase):
    def setUp(self):
        clean_up()

        # Initialise test repository
        self.working_repo = Repo.init(TEST_DIR)
        create_dummy_file(self.working_repo)
        test_branch = self.working_repo.create_head("TEST_BRANCH")
        self.working_repo.head.reference = test_branch

        # Initialise VC manager under test
        self.vc = GitVersionControl(TEST_DIR, self.working_repo, is_local=True)
        self.vc.setup()

    def test_placeholder(self):
        pass
