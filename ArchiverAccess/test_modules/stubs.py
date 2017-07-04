class ArchiverDataStub(object):
    def __init__(self, initial_values, values):
        self._initial_values = initial_values
        if values is None:
            self._values = []
        else:
            self._values = values

    def initial_values(self, pv_names, time):
        initial_values = []
        for pvname in pv_names:
            initial_values.append(self._initial_values[pvname])
        return initial_values

    def changes_generator(self, pv_names, time_period):
        for value in self._values:

            yield (value[0], pv_names.index(value[1]), value[2])


class FileStub(object):
    """
    Mimic the python file object
    """
    file_contents = None
    filename = ""
    file_open = False

    def __init__(self, filename):
        FileStub.file_contents = None
        FileStub.filename = filename
        FileStub.file_open = False

    def __enter__(self):
        FileStub.file_open = True
        FileStub.file_contents = []
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        FileStub.file_open = False

    def write(self, line):
        FileStub.file_contents.extend(line.splitlines())