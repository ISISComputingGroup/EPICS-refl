import os
import shutil
import time
import unittest

from watchdog.events import *
from ConfigVersionControl.git_version_control import GitVersionControl
from git import Repo

TEST_DIR = os.path.abspath(os.path.join(__file__, "..", "test_git"))
TEST_BRANCH = "TEST_BRANCH"


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
        # Call in case tearDown was not called previously because of failing tests
        clean_up()

        # Initialise test repository
        self.working_repo = Repo.init(TEST_DIR)
        create_dummy_file(self.working_repo)
        self.test_branch = self.working_repo.create_head(TEST_BRANCH)
        self.working_repo.head.reference = self.test_branch

    def tearDown(self):
        self.working_repo.close()
        clean_up()

    def test_repo_is_on_correct_branch(self):
        assert self.working_repo.active_branch == self.test_branch

    def test_can_set_up_vc_manager(self):
        try:
            self.vc = GitVersionControl(TEST_DIR, self.working_repo, is_local=True)
            self.vc.setup()
        except Exception:
            self.fail("myFunc() raised Exception unexpectedly!")

    def test_branch_is_allowed(self):
        self.vc = GitVersionControl(TEST_DIR, self.working_repo, is_local=True)
        self.vc.setup()

        assert self.vc.branch_allowed(TEST_BRANCH)

        #  FILEPATH_MANAGER.initialise(TEST_DIRECTORY, SCRIPTS_DIRECTORY, SCHEMA_DIR)
        #  self.file_manager = MockConfigurationFileManager()
        #  self.config_list_manager = MagicMock()
        #  self.is_component = False
        #  self.eh = ConfigFileEventHandler(RLock(), self.config_list_manager, self.is_component)
