import os
import unittest
from mock import Mock
from git_version_control import CommitMessageProvider


class TestMessageProvider(unittest.TestCase):

    @staticmethod
    def add_comma(string):
        return ", " + string;

    def setUp(self):
        self.mp = CommitMessageProvider()
        self.diff = []

    def test_WHEN_initialised_THEN_message_is_empty(self):
        # Assert
        assert len(self.mp.get_commit_message(self.diff)) == 0

    def test_WHEN_unclassified_item_modified_THEN_other_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("some_folder", "file.txt")
        changed = Mock(a_rawpath=file_path, new_file=False)
        self.diff.append(changed)

        expected_msg = self.mp.OTHER_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_config_modified_THEN_config_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "configurations", "config_name", "file.xml")
        changed = Mock(a_rawpath=file_path, new_file=False)
        self.diff.append(changed)

        expected_msg = self.mp.CONFIGS_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_config_deleted_THEN_config_deleted_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "configurations", "config_name", "file.xml")
        changed = Mock(a_rawpath=file_path, new_file=True)
        self.diff.append(changed)

        expected_msg = self.mp.CONFIGS_DELETED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_non_xml_file_in_config_dir_modified_THEN_other_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "configurations", "config_name", "file.txt")
        changed = Mock(a_rawpath=file_path, new_file=False)
        self.diff.append(changed)

        expected_msg = self.mp.OTHER_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_non_xml_file_in_config_dir_deleted_THEN_other_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "configurations", "config_name", "file.txt")
        changed = Mock(a_rawpath=file_path, new_file=True)
        self.diff.append(changed)

        expected_msg = self.mp.OTHER_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg
    def test_WHEN_comp_modified_THEN_comps_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "components", "comp_name", "file.xml")
        changed = Mock(a_rawpath=file_path, new_file=False)
        self.diff.append(changed)

        expected_msg = self.mp.COMPS_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_comp_deleted_THEN_comps_deleted_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "components", "comp_name", "file.xml")
        changed = Mock(a_rawpath=file_path, new_file=True)
        self.diff.append(changed)

        expected_msg = self.mp.COMPS_DELETED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_non_xml_file_in_comp_dir_modified_THEN_other_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "components", "config_name", "file.txt")
        changed = Mock(a_rawpath=file_path, new_file=False)
        self.diff.append(changed)

        expected_msg = self.mp.OTHER_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_non_xml_file_in_comp_dir_deleted_THEN_other_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "components", "config_name", "file.txt")
        changed = Mock(a_rawpath=file_path, new_file=True)
        self.diff.append(changed)

        expected_msg = self.mp.OTHER_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_synoptic_modified_THEN_synoptics_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "synoptics", "synoptic_name.xml")
        changed = Mock(a_rawpath=file_path, new_file=False)
        self.diff.append(changed)

        expected_msg = self.mp.SYN_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_synoptic_deleted_THEN_synoptics_deleted_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "synoptics", "synoptic_name.xml")
        changed = Mock(a_rawpath=file_path, new_file=True)
        self.diff.append(changed)

        expected_msg = self.mp.SYN_DELETED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_non_xml_file_in_comp_dir_modified_THEN_other_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "synoptics", "synoptic_name.txt")
        changed = Mock(a_rawpath=file_path, new_file=False)
        self.diff.append(changed)

        expected_msg = self.mp.OTHER_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_non_xml_file_in_comp_dir_deleted_THEN_other_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "synoptics", "synoptic_name.txt")
        changed = Mock(a_rawpath=file_path, new_file=True)
        self.diff.append(changed)

        expected_msg = self.mp.OTHER_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_device_screens_modified_THEN_device_screens_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "devices", "screens.xml")
        changed = Mock(a_rawpath=file_path, new_file=False)
        self.diff.append(changed)

        expected_msg = self.mp.DEVICES_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_device_screens_deleted_THEN_device_screens_deleted_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "devices", "screens.xml")
        changed = Mock(a_rawpath=file_path, new_file=True)
        self.diff.append(changed)

        expected_msg = self.mp.DEVICES_DELETED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_non_device_screens_file_in_comp_dir_modified_THEN_other_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "devices", "something_else.xml")
        changed = Mock(a_rawpath=file_path, new_file=False)
        self.diff.append(changed)

        expected_msg = self.mp.OTHER_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_non_device_screens_in_comp_dir_deleted_THEN_other_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Configurations", "devices", "something_else.xml")
        changed = Mock(a_rawpath=file_path, new_file=True)
        self.diff.append(changed)

        expected_msg = self.mp.OTHER_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_scripts_modified_THEN_scripts_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Python", "some_script.py")
        changed = Mock(a_rawpath=file_path, new_file=False)
        self.diff.append(changed)

        expected_msg = self.mp.SCRIPTS_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_scripts_deleted_THEN_scripts_deleted_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Python", "some_script.py")
        changed = Mock(a_rawpath=file_path, new_file=True)
        self.diff.append(changed)

        expected_msg = self.mp.SCRIPTS_DELETED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_non_script_file_in_comp_dir_modified_THEN_other_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Python", "some_file.txt")
        changed = Mock(a_rawpath=file_path, new_file=False)
        self.diff.append(changed)

        expected_msg = self.mp.OTHER_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_non_script_in_comp_dir_deleted_THEN_other_modified_in_commit_message(self):
        # Arrange
        file_path = os.path.join("Python", "some_file.txt")
        changed = Mock(a_rawpath=file_path, new_file=True)
        self.diff.append(changed)

        expected_msg = self.mp.OTHER_MODIFIED

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg

    def test_WHEN_multiple_events_THEN_all_relevant_messages_in_commit_message(self):
        # Arrange
        paths = []
        paths.append(os.path.join("Configurations", "configurations", "config_name", "file.xml"))
        paths.append(os.path.join("Configurations", "components", "comp_name", "file.xml"))
        paths.append(os.path.join("Configurations", "synoptics", "synoptic_name.xml"))
        paths.append(os.path.join("Configurations", "devices", "screens.xml"))
        paths.append(os.path.join("Python", "some_script.py"))
        paths.append(os.path.join("some_folder", "file.txt"))
        for path in paths:
            self.diff.append(Mock(a_rawpath=path, new_file=False))
            self.diff.append(Mock(a_rawpath=path, new_file=True))

        expected_msg = self.mp.CONFIGS_MODIFIED + self.add_comma(
            self.mp.CONFIGS_DELETED) + self.add_comma(self.mp.COMPS_MODIFIED) + self.add_comma(
            self.mp.COMPS_DELETED) + self.add_comma(self.mp.SYN_MODIFIED) + self.add_comma(
            self.mp.SYN_DELETED) + self.add_comma(self.mp.DEVICES_MODIFIED) + self.add_comma(
            self.mp.DEVICES_DELETED) + self.add_comma(self.mp.SCRIPTS_MODIFIED) + self.add_comma(
            self.mp.SCRIPTS_DELETED) + self.add_comma(self.mp.OTHER_MODIFIED)

        # Act
        actual_msg = self.mp.get_commit_message(self.diff)

        # Assert
        assert actual_msg == expected_msg