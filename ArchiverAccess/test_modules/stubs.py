from ArchiverAccess.archiver_data_source import ArchiverDataSource


class ArchiverDataStub(ArchiverDataSource):
    def __init__(self,
                 initial_values=None,
                 values=None,
                 initial_archiver_data_value=None,
                 data_changes=None,
                 sample_ids=None):
        super(ArchiverDataStub, self).__init__(None)
        self.from_sample_id = []
        self.to_sample_id = []
        self._initial_values = initial_values
        if values is None:
            self._values = []
        else:
            self._values = values

        self._initial_archiver_data_value = initial_archiver_data_value
        self._data_changes = data_changes
        self._data_change_index = 0
        self._sample_ids = sample_ids
        self._sample_id_index = 0

    def initial_values(self, pv_names, time):
        initial_values = []
        for pvname in pv_names:
            initial_values.append(self._initial_values[pvname])
        return initial_values

    def changes_generator(self, pv_names, time_period):
        for value in self._values:
            yield (value[0], pv_names.index(value[1]), value[2])

    def get_latest_sample_time(self, time=None):
        self._sample_id_index += 1
        return self._sample_ids[self._sample_id_index - 1]

    def logging_changes_for_sample_id_generator(self, pv_names, from_sample_id, to_sample_id):
        self.from_sample_id.append(from_sample_id)
        self.to_sample_id.append(to_sample_id)
        for data_change in self._data_changes[self._data_change_index]:
            yield data_change
        self._data_change_index += 1

    def initial_archiver_data_values(self, pv_names, time):
        return self._initial_archiver_data_value


class FileStub(object):
    """
    Mimic the python file object
    """
    file_contents = None
    file_contents_to_read = []
    filename = ""
    file_open = False
    raise_on_write = None

    def __init__(self, filename, mode=""):
        FileStub.file_contents = None
        FileStub.filename = filename
        FileStub.file_open = False
        self.read_line_index = 0

    def __enter__(self):
        FileStub.file_open = True
        FileStub.file_contents = []
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        FileStub.file_open = False

    def write(self, line):
        if FileStub.raise_on_write is not None:
            raise FileStub.raise_on_write
        FileStub.file_contents.extend(line.splitlines())

    def readline(self):
        next_line = FileStub.file_contents_to_read[self.read_line_index]
        self.read_line_index += 1
        return "{0}\n".format(next_line)

    @classmethod
    def add_file(cls, file_contents):
        FileStub.file_contents_to_read = file_contents
