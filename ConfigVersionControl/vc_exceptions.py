class NotUnderVersionControl(Exception):
    def __init__(self, directory):
        self._dir = directory

    def __str__(self):
        return "Folder is not under version control: " + repr(self._dir)


class GitPullFailed(Exception):
    def __str__(self):
        return "Git pull command failed, remote server may be down"