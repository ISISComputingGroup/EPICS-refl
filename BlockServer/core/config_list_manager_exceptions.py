class ConfigListManagerException(Exception):
    def __init__(self,err):
        self.message = str(err)

    def __str__(self):
        return self.message


class InvalidDeleteException(ConfigListManagerException):
    def __init__(self, err):
        self.message = str(err)


class RemoveFromVersionControlException(ConfigListManagerException):
    def __init__(self,type,err):
        self.message = "Unable to remove %s from version control: %s" % (type, str(err))