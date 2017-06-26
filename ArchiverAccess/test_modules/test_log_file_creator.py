# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php

import unittest

from hamcrest import *

from ArchiverAccess.archive_data_file_creator import ArchiveDataFileCreator
from ArchiverAccess.configuration import ConfigBuilder


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


class TestlogFileCreator(unittest.TestCase):

    def test_GIVEN_config_is_just_constant_header_line_WHEN_write_THEN_values_are_written_to_file(self):
        expected_header_line = "expected_header_line a line of goodness :-)"
        config = ConfigBuilder("filename.txt").header(expected_header_line).build()
        file_creator = ArchiveDataFileCreator(config, FileStub)

        file_creator.write()

        assert_that(FileStub.file_contents, is_([expected_header_line]))

    def test_GIVEN_config_contains_plain_filename_WHEN_write_THEN_file_is_opened(self):
        expected_filename = "filename.txt"
        config = ConfigBuilder(expected_filename).build()
        file_creator = ArchiveDataFileCreator(config, FileStub)

        file_creator.write()

        assert_that(FileStub.filename, is_(expected_filename))
