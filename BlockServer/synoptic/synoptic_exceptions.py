class VersionControlException(Exception):
    def __init__(self, err):
        self.message = str(err)

    def __str__(self):
        return self.message


class AddToVersionControlException(VersionControlException):
    def __init__(self, err):
        self.message = "Unable to add synoptic to version control: %s" % str(err)


class CommitToVersionControlException(VersionControlException):
    def __init__(self, err):
        self.message = "Unable to commit synoptic changes to version control: %s" % str(err)


class RemoveFromVersionControlException(VersionControlException):
    def __init__(self, err):
        self.message = "Unable to delete synoptic changes from version control: %s" % str(err)
