class MaxAttemptsExceededException(Exception):
    def __init__(self, err=""):
        self.message = str(err)

    def __str__(self):
        return self.message
