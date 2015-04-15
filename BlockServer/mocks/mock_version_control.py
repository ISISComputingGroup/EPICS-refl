import os
import shutil


class MockVersionControl(object):

    def add(self, file_path):
        pass

    def remove(self, file_path):
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        elif os.path.isfile(file_path):
            os.remove(file_path)

    def commit(self, commit_comment):
        pass

    def update(self, update_path=""):
        pass