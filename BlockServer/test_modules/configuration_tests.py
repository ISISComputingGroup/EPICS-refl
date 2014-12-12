import unittest
import os

from config.configuration import Configuration
from config.configuration import GRP_NONE

from mocks.mock_configuration import MockConfigurationFileManager
from mocks.mock_configuration import MockConfigurationXmlConverter
from mocks.mock_configuration import MockConfigurationJsonConverter

PVPREFIX = 'MYPVPREFIX'

MACROS = {
    "$(MYPVPREFIX)": os.environ[PVPREFIX],
}

#Args are : name, pv, group, local and visible
NEW_BLOCK_ARGS = {'name': "TESTBLOCK1", 'pv': "PV1", 'group': "GROUP1", 'local': True, 'visible': True}
NEW_BLOCK_ARGS_2 = {'name': "TESTBLOCK2", 'pv': "PV2", 'group': "GROUP2", 'local': True, 'visible': True}

# TODO write tests for ConfigurationFileManager (config/file_manager.py)


class TestConfigurationSequence(unittest.TestCase):
    def setUp(self):
        # Create a new configuration
        self.file_manager = MockConfigurationFileManager()
        self.json_converter = MockConfigurationJsonConverter()
        self.config = Configuration(MACROS)

    def tearDown(self):
        pass

    def test_adding_a_block_and_getting_block_names_returns_the_name_of_the_block(self):
        # arrange
        cf = self.config
        block_args = NEW_BLOCK_ARGS
        block_name = block_args['name']
        # act
        cf.add_block(**block_args)
        blocks = cf.blocks.keys()
        # assert
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0], block_name.lower())

    def test_adding_a_block_and_removing_it_gives_an_empty_list_of_block_names(self):
        # arrange
        cf = self.config
        block_args = NEW_BLOCK_ARGS
        block_name = block_args['name']
        # act
        cf.add_block(**block_args)
        cf.remove_block(block_name)
        blocks = cf.blocks
        # assert
        self.assertEqual(len(blocks), 0)

    def test_adding_a_block_also_adds_its_associated_group(self):
        # arrange
        cf = self.config
        block_args = NEW_BLOCK_ARGS
        group_name = block_args['group']
        # act
        cf.add_block(**block_args)
        groups = cf.groups.keys()
        # assert
        self.assertEqual(len(groups), 1)
        self.assertTrue(group_name.lower() in groups)

    def test_removing_a_block_does_not_remove_its_group(self):
        # arrange
        cf = self.config
        block_args = NEW_BLOCK_ARGS
        block_name = block_args['name']
        group_name = block_args['group']
        # act
        cf.add_block(**block_args)
        cf.remove_block(block_name)
        groups = cf.groups.keys()
        # assert
        self.assertEqual(len(groups), 1)
        self.assertTrue(group_name.lower() in groups)

    def test_adding_the_same_block_twice_raises_exception(self):
        # arrange
        cf = self.config
        block_args = NEW_BLOCK_ARGS
        # act
        cf.add_block(**block_args)
        # assert
        self.assertRaises(Exception, cf.add_block, *block_args)

    def test_removing_a_nonexistant_block_raises_exception(self):
        # arrange
        cf = self.config
        block_name = "TESTBLOCK1"
        # assert
        self.assertRaises(Exception, cf.remove_block, block_name)

    def test_editing_block_correctly_changes_block_name(self):
        # arrange
        cf = self.config
        old_name = "TESTBLOCK1"
        new_name = "TESTBLOCK2"
        #act
        cf.add_block(old_name, "", "", True)
        cf.edit_block(old_name, "", True, new_name)
        blocks = cf.blocks.keys()
        #assert
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0], new_name.lower())

    def test_editing_a_nonexistant_block_raises_exception(self):
        # arrange
        cf = self.config
        edit_args = ["TESTBLOCK1", "", "", True, ""]
        # assert
        self.assertRaises(Exception, cf.edit_block, *edit_args)

    def test_editing_block_pv_correctly_changes_pv(self):
        # arrange
        cf = self.config
        block_name = "TESTBLOCK1"
        old_pv = "PV1"
        new_pv = "PV2"
        #act
        cf.add_block(block_name, old_pv, "GRP", local=True)
        cf.edit_block(block_name, new_pv, local=True)
        pv_name = cf.blocks[block_name.lower()].pv
        #assert
        self.assertEqual(pv_name, new_pv)

    def test_editing_block_visible_correctly_changes_visible(self):
        # arrange
        cf = self.config
        block_name = "TESTBLOCK1"
        #act
        cf.add_block(block_name, "PV1", "GRP", local=True, visible=True)
        cf.edit_block(block_name, "PV1", local=True, visible=False)
        visible = cf.blocks[block_name.lower()].visible
        #assert
        self.assertFalse(visible)

    def test_editing_block_with_blank_new_name_doesnt_change_name(self):
        # arrange
        cf = self.config
        block_args = NEW_BLOCK_ARGS
        block_name = block_args['name']
        edit_args = {'name': block_name}
        # act
        cf.add_block(**block_args)
        cf.edit_block(**edit_args)
        blocks = cf.blocks.keys()
        # assert
        self.assertEqual(blocks[0], block_name.lower())

    def test_editing_block_with_same_name_as_existing_block_raises_exception(self):
        # arrange
        cf = self.config
        block_args_1 = NEW_BLOCK_ARGS
        block_args_2 = NEW_BLOCK_ARGS_2
        block_name_1 = block_args_1['name']
        block_name_2 = block_args_2['name']
        edit_args = {'name': block_name_1, 'new_name': block_name_2}
        # act
        cf.add_block(**block_args_1)
        cf.add_block(**block_args_2)
        #assert
        self.assertRaises(Exception, cf.edit_block, *edit_args)

    def test_adding_ioc_correctly_adds_to_ioc_list(self):
        # arrange
        cf = self.config
        ioc_name = "TESTIOC"
        # act
        cf.add_ioc(ioc_name)
        iocs = cf.iocs
        # assert
        self.assertEqual(len(iocs), 1)
        self.assertEqual(iocs["TESTIOC"].name, ioc_name)

    def test_adding_the_same_ioc_twice_does_not_raise_exception(self):
        # arrange
        cf = self.config
        ioc_name = "TESTIOC"
        # act
        cf.add_ioc(ioc_name)
        # assert
        try:
            cf.add_ioc(ioc_name)
        except:
            self.fail("Adding the same ioc twice raised Exception unexpectedly!")

    def test_removing_ioc_removes_it_from_ioc_list(self):
        # arrange
        cf = self.config
        ioc_name = "TESTIOC"
        # act
        cf.add_ioc(ioc_name)
        cf.remove_ioc(ioc_name)
        iocs = cf.iocs
        # assert
        self.assertEqual(len(iocs), 0)

    def test_removing_non_existant_ioc_does_not_raise_exception(self):
        # arrange
        cf = self.config
        ioc_name = "TESTIOC"
        # assert
        try:
            cf.remove_ioc(ioc_name)
        except:
            self.fail("Removing non-existant IOC raised Exception unexpectedly!")

    def test_get_blocks_names_returns_empty_list_when_no_blocks(self):
        # arrange
        cf = self.config
        # act
        block_names = cf.blocks.keys()
        # assert
        self.assertEqual(len(block_names), 0)


if __name__ == '__main__':
    #start blockserver
    unittest.main()
