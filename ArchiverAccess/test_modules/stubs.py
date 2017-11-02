from ArchiverAccess.archiver_data_source import ArchiverDataSource


class ArchiverDataStub(ArchiverDataSource):
    def __init__(self,
                 initial_values=None,
                 values=None,
                 initial_archiver_data_value=None,
                 data_changes=None,
                 sample_ids=None):
        """

        Args:
            initial_values: list of values in pv order for at t=0 of data changes
            values: changes to pv values
            initial_archiver_data_value:
            data_changes: returns from calls to the logging_changes_for_sample_id_generator each return is a list of data changes in a list of
                each data change is a tuple of change time, index and new value
            sample_ids: sample ids to return
        """
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
    Mimic the python file object (inc file system effects) call clear on setup to avoid persisted state
    """

    file_contents = {}
    file_open = {}
    raise_on_write = {}

    def __init__(self, filename, mode="r"):
        self.filename = filename
        FileStub.file_open[filename] = False
        self.mode = mode
        self.read_line_index = 0

    def __enter__(self):
        FileStub.file_open[self.filename] = True
        if self.mode == "w" or self.filename not in FileStub.file_contents:
            FileStub.file_contents[self.filename] = []
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        FileStub.file_open[self.filename] = False

    def write(self, line):
        if self.filename in FileStub.raise_on_write:
            raise FileStub.raise_on_write[self.filename]
        FileStub.file_contents[self.filename].extend(line.splitlines())

    def readline(self):
        file_contents_for_file = FileStub.file_contents[self.filename]
        next_line = file_contents_for_file[self.read_line_index]
        self.read_line_index += 1
        return "{0}\n".format(next_line)

    @classmethod
    def add_file(cls, file_contents, filename):
        FileStub.file_contents[filename] = file_contents

    @classmethod
    def clear(cls):
        FileStub.file_contents = {}
        FileStub.file_open = {}
        FileStub.raise_on_write = {}

    @classmethod
    def contents_of_only_file(cls):
        assert len(FileStub.file_contents) == 1, \
            "Number of files created is not 1. Filenames are {0}".format(FileStub.file_contents.keys())
        return FileStub.file_contents.values()[0]
