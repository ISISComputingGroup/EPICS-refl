import unittest
import os
import shutil
import json
from time import sleep
import xml.etree.ElementTree as eTree
from collections import OrderedDict
from channel_access import caget, caput
from utilities import compress_and_hex, dehex_and_decompress

#This assumes the block_server is run using start_blockserver_for_tests.bat
#and the command line is set up to use EPICS

MY_PV_PREFIX = os.environ['MYPVPREFIX']
BLOCKSERVER_PREFIX = "CS:BLOCKSERVER:"
TEST_CONFIG = "TESTSCONFIG"


def prefix_pv_name(name):
    """Adds the instrument prefix to the specified PV"""
    return MY_PV_PREFIX + BLOCKSERVER_PREFIX + name


def write_to_pv(pvname, value):
    caput(prefix_pv_name(pvname), value)


def get_pv(pvname, to_string=False):
    return caget(prefix_pv_name(pvname), as_string=to_string)


def get_groups_and_blocks():
    ans = dehex_and_decompress(get_pv("GROUPINGS", True))
    groups = OrderedDict()
    root = eTree.fromstring(ans)
    grps = root.findall("./group")
    for g in grps:
        gname = g.attrib['name']
        blocks = []
        blks = g.findall("./block")
        for b in blks:
            bname = b.attrib['name']
            blocks.append(bname)
        groups[gname] = blocks
    return groups


def create_grouping(groups):
    struct = []
    for grp, blocks in groups.iteritems():
        d = dict()
        d["name"] = grp
        d["blocks"] = blocks
        struct.append(d)    
    ans = json.dumps(struct)
    return ans


class TestBlockServerSequence(unittest.TestCase):
    def setUp(self):
        #Clear the configuration
        write_to_pv("CLEAR_CONFIG", 1)
        #Delete the test config
        config = os.path.abspath(TEST_CONFIG) + "\\"
        if os.path.isdir(config):
            shutil.rmtree(config)
            
    def tearDown(self):
        #Delete the test config
        config = os.path.abspath(TEST_CONFIG) + "\\"
        if os.path.isdir(config):
            shutil.rmtree(config)

    def test_clear_config(self):
        #Get the blocks - should be ''
        ans = get_pv("BLOCKS", True)
        self.assertTrue(ans == '')
        #Get the groups xml and check there are no groups
        grps = get_groups_and_blocks()
        self.assertTrue(len(grps) == 0)
        #Check config name is ''
        ans = get_pv("CONFIG", True)
        self.assertTrue(ans == '')
        
    def test_add_block_nogroup(self):
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK;SOMEPV;NONE;LOC")
        ans = get_pv("BLOCKS", True)
        self.assertTrue(ans == 'MYTESTBLOCK')
        
    def test_add_block_group(self):
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK;SOMEPV;TESTGROUP;LOC")
        ans = get_pv("BLOCKS", True)
        self.assertTrue(ans == 'MYTESTBLOCK')
        grps = get_groups_and_blocks()
        self.assertTrue(len(grps) == 1)
        self.assertTrue(grps.keys()[0] == "TESTGROUP")
        blks = grps[grps.keys()[0]]
        self.assertTrue(len(blks) == 1)
        self.assertTrue(blks[0] == "MYTESTBLOCK")
        
    def test_adding_multiple_blocks(self):
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK1;SOMEPV;TESTGROUP1;LOC")
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK2;SOMEPV;TESTGROUP1;LOC")
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK3;SOMEPV;TESTGROUP2;LOC")
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK4;SOMEPV;TESTGROUP2;LOC")
        grps = get_groups_and_blocks()
        self.assertTrue(len(grps) == 2)
        blks = grps[grps.keys()[0]]
        self.assertTrue(len(blks) == 2)
        self.assertTrue(blks[0] == "MYTESTBLOCK1")
        self.assertTrue(blks[1] == "MYTESTBLOCK2")
        blks = grps[grps.keys()[1]]
        self.assertTrue(len(blks) == 2)
        self.assertTrue(blks[0] == "MYTESTBLOCK3")
        self.assertTrue(blks[1] == "MYTESTBLOCK4")
        
    def test_remove_block(self):
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK1;SOMEPV;TESTGROUP1;LOC")
        sleep(1)
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK2;SOMEPV;TESTGROUP1;LOC")
        ans = get_pv("BLOCKS", True)
        self.assertTrue(len(ans.split(';')) == 2)
        write_to_pv("REMOVE_BLOCK", "MYTESTBLOCK1")
        ans = get_pv("BLOCKS", True)
        self.assertTrue(len(ans.split(';')) == 1)
        self.assertTrue(ans == "MYTESTBLOCK2")
        grps = get_groups_and_blocks()
        self.assertTrue(len(grps) == 1)
        blks = grps[grps.keys()[0]]
        self.assertTrue(len(blks) == 1)
        self.assertTrue(blks[0] == "MYTESTBLOCK2")
        
    def test_edit_block(self):
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK1;SOMEPV;TESTGROUP1;LOC")
        write_to_pv("EDIT_BLOCK", "MYTESTBLOCK1;SOMEPV;TESTGROUP2;LOC;MYRENAMEDBLOCK")
        ans = get_pv("BLOCKS", True)
        self.assertTrue(ans == "MYRENAMEDBLOCK")
        grps = get_groups_and_blocks()
        self.assertTrue(grps["TESTGROUP2"][0] == "MYRENAMEDBLOCK")
        
    def test_get_pv(self):
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK1;SOMEPV;TESTGROUP1;LOC")
        write_to_pv("GET_PV", "MYTESTBLOCK1")
        ans = get_pv("GET_PV", True)
        self.assertTrue(ans == "SOMEPV")
        
    def test_save_and_load_config(self):
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK1;SOMEPV;TESTGROUP1;LOC")
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK2;SOMEPV;TESTGROUP1;LOC")
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK3;SOMEPV;TESTGROUP2;LOC")
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK4;SOMEPV;TESTGROUP2;LOC")
        write_to_pv("SAVE_CONFIG", TEST_CONFIG)
        ans = get_pv("CONFIG", True)
        self.assertTrue(ans == TEST_CONFIG)
        write_to_pv("CLEAR_CONFIG", 1)
        ans = get_pv("CONFIG", True)
        self.assertTrue(ans == '')
        write_to_pv("LOAD_CONFIG", TEST_CONFIG)
        grps = get_groups_and_blocks()
        self.assertTrue(len(grps) == 3)
        self.assertTrue(grps.keys()[0] == "TESTGROUP1")
        self.assertTrue(grps.keys()[1] == "TESTGROUP2")
        self.assertTrue(grps.keys()[2] == "NONE")
        blks = grps[grps.keys()[0]]
        self.assertTrue(len(blks) == 2)
        self.assertTrue(blks[0] == "MYTESTBLOCK1")
        self.assertTrue(blks[1] == "MYTESTBLOCK2") 
        blks = grps[grps.keys()[1]]
        self.assertTrue(len(blks) == 2)
        self.assertTrue(blks[0] == "MYTESTBLOCK3")
        self.assertTrue(blks[1] == "MYTESTBLOCK4") 
        
    def test_block_prefix(self):
        ans = get_pv("BLOCK_PREFIX", True)
        self.assertTrue(ans == MY_PV_PREFIX + "CS:SB:")
        
    def test_new_groupings(self):
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK1;SOMEPV;TESTGROUP1;LOC")
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK2;SOMEPV;TESTGROUP1;LOC")
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK3;SOMEPV;TESTGROUP2;LOC")
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK4;SOMEPV;TESTGROUP2;LOC")
        #Create a new grouping by moving MYTESTBLOCK2 to TESTGROUP2
        groups = OrderedDict()
        groups["TESTGROUP1"] = ["MYTESTBLOCK1"]
        groups["TESTGROUP2"] = ["MYTESTBLOCK2", "MYTESTBLOCK3", "MYTESTBLOCK4"]
        js = create_grouping(groups)
        write_to_pv("NEW_GROUPINGS",  compress_and_hex(js))
        #Get the new groupings from the block_server
        grps = get_groups_and_blocks()
        self.assertTrue(len(grps) == 3)
        self.assertTrue(grps.keys()[0] == "TESTGROUP1")
        self.assertTrue(grps.keys()[1] == "TESTGROUP2")
        self.assertTrue(grps.keys()[2] == "NONE")
        blks = grps[grps.keys()[0]]
        self.assertTrue(len(blks) == 1)
        self.assertTrue(blks[0] == "MYTESTBLOCK1")
        blks = grps[grps.keys()[1]]
        self.assertTrue(len(blks) == 3)
        self.assertTrue(blks[0] == "MYTESTBLOCK2") 
        self.assertTrue(blks[1] == "MYTESTBLOCK3")
        self.assertTrue(blks[2] == "MYTESTBLOCK4") 
        
    def test_add_iocs(self):
        write_to_pv("ADD_IOC", "SIMPLE")
        iocs = get_pv("CONFIG_IOCS", True)
        self.assertTrue("SIMPLE" in iocs)
        
    def test_add_remove_iocs(self):
        write_to_pv("ADD_IOC", "SIMPLE")
        iocs = get_pv("CONFIG_IOCS", True)
        self.assertTrue("SIMPLE" in iocs)
        write_to_pv("REMOVE_IOC", "SIMPLE")
        iocs = get_pv("CONFIG_IOCS", True)
        self.assertTrue("SIMPLE" not in iocs)
        
    def test_save_load_iocs_config(self):
        write_to_pv("ADD_IOC", "SIMPLE")
        iocs = get_pv("CONFIG_IOCS", True)
        self.assertTrue("SIMPLE" in iocs)
        write_to_pv("SAVE_CONFIG", TEST_CONFIG)
        ans = get_pv("CONFIG", True)
        self.assertTrue(ans == TEST_CONFIG)
        write_to_pv("CLEAR_CONFIG", 1)
        ans = get_pv("CONFIG", True)
        self.assertTrue(ans == '')

        write_to_pv("SAVE_NEW_CONFIG", TEST_CONFIG)
        ans = get_pv("CONFIG", True)
        self.assertTrue(ans == '')
        list = get_pv("CONFIGS", True)
        self.assertTrue(TEST_CONFIG in list)

        write_to_pv("LOAD_CONFIG", TEST_CONFIG)
        iocs = get_pv("CONFIG_IOCS", True)
        self.assertTrue("SIMPLE" in iocs) 

    def test_start_stop_iocs(self):
        pass
        
    def test_get_blocks_json(self):
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK1;SOMEPV1;NONE;LOC")
        write_to_pv("ADD_BLOCK", "MYTESTBLOCK2;MYPVPREFIX:IOCNAME:SOMEPV2;NONE;REM")
        blks = json.loads(dehex_and_decompress(get_pv("BLOCKS_JSON", True)))
        self.assertTrue(len(blks.keys()) == 2)
        self.assertTrue(blks["MYTESTBLOCK1"]["pv"] == MY_PV_PREFIX + "SOMEPV1")
        self.assertTrue(blks["MYTESTBLOCK2"]["pv"] == "MYPVPREFIX:IOCNAME:SOMEPV2") 

if __name__ == '__main__': 
    #start blockserver
    unittest.main()