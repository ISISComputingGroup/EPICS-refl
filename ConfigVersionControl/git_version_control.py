# Version Control class for dealing with git file operations
import stat
import socket
from git import *
from constants import PUSH_RETRY_INTERVAL, PUSH_BASE_INTERVAL
from vc_exceptions import NotUnderVersionControl, GitPullFailed, NotUnderAllowedBranch
from threading import Thread, RLock
from time import sleep
from server_common.utilities import print_and_log


class GitVersionControl:

    def __init__(self, working_directory):
        self._wd = working_directory

        # Check repo
        try:
            self.repo = Repo(self._wd, search_parent_directories=True)
        except Exception as e:
            # Not a valid repository
            raise NotUnderVersionControl(self._wd)

        if not self._branch_allowed(str(self.repo.active_branch)):
            raise NotUnderAllowedBranch()

        self._unlock()
        self.remote = self.repo.remotes.origin
        config_writer = self.repo.config_writer()
        # Set git repository to ignore file permissions otherwise will reset to read only
        config_writer.set_value("core", "filemode", False)
        self._pull()

        # Start a background thread for pushing
        self._push_required = False
        self._push_lock = RLock()
        push_thread = Thread(target=self._push, args=())
        push_thread.daemon = True  # Daemonise thread
        push_thread.start()

    def _branch_allowed(self, branch_name):
        """Checks that the branch is allowed to be pushed

        Args:
            branch_name (string): The name of the current branch
        Returns:
            bool : Whether the branch is allowed
        """
        branch_name = branch_name.lower()

        if "master" in branch_name:
            return False

        if branch_name.startswith("nd") and branch_name != socket.gethostname().lower():
            # You're trying to push to a different instrument
            return False

        return True

    def _unlock(self):
        # Removes index.lock if it exists, and it's not being used
        lock_file_path = os.path.join(self.repo.git_dir, "index.lock")
        if os.path.exists(lock_file_path):
            try:
                os.remove(lock_file_path)
            except Exception as err:
                print_and_log("Unable to remove lock from version control repository: %s" %
                              lock_file_path, "MINOR")
            else:
                print_and_log("Lock removed from version control repository: %s" % lock_file_path, "INFO")

    # TODO: Waits with no timeout here!!
    def info(self, working_directory):
        # returns some information on the repository
        print self.repo.git.status()

    def add(self, path):
        # adds a file to the repository
        # Add needs write capability on .git folder
        try:
            self.repo.index.add([path])
        except WindowsError as e:
            # Most Likely Access Denied
            self._set_permissions()
            self.repo.index.add([path])

    def commit(self, working_directory, commit_comment):
        # commits changes to a file to the repository and pushes
        self.repo.index.commit(commit_comment)
        with self._push_lock:
            self._push_required = True

    def update(self, update_path):
        # reverts folder to the remote repository
        self._pull()
        if self.repo.is_dirty():
            self.repo.index.checkout()

    def remove(self, path):
        delete_list = []
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path, topdown=False):
                for f in files:
                    delete_list.append(os.path.abspath(os.path.join(root, f)))
                for d in dirs:
                    delete_list.append(os.path.abspath(os.path.join(root, d)))
        else:
            delete_list.append(path)
        self.repo.index.remove(delete_list, True)

    def _pull(self):
        try:
            self.remote.pull()
        except GitCommandError as e:
            # Most likely server issue
            print_and_log("Unable to pull configurations from remote repo", "MINOR")
            raise GitPullFailed()

    def _set_permissions(self):
        git_path = self.repo.git_dir
        os.chmod(git_path, stat.S_IWRITE)
        for root, dirs, files in os.walk(git_path):
            for d in dirs:
                os.chmod(os.path.join(root, d), stat.S_IWRITE)
            for f in files:
                os.chmod(os.path.join(root, f), stat.S_IWRITE)

    def _push(self):
        push_interval = PUSH_BASE_INTERVAL
        first_failure = True

        while 1:
            with self._push_lock:
                if self._push_required:
                    try:
                        self.remote.push()
                        self._push_required = False
                        push_interval = PUSH_BASE_INTERVAL
                        first_failure = True

                    except GitCommandError as e:
                        # Most likely issue connecting to server, increase timeout, notify if it's the first time
                        push_interval = PUSH_RETRY_INTERVAL
                        if first_failure:
                            print_and_log("Unable to push config changes, will retry in %i seconds"
                                          % PUSH_RETRY_INTERVAL, "MINOR")
                            first_failure = False

            sleep(push_interval)