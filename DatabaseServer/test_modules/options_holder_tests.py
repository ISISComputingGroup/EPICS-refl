import unittest
from options_holder import OptionsHolder
from options_loader import OptionsLoader

OPTIONS_PATH = "./test_files/"


class TestOptionsHolderSequence(unittest.TestCase):

    def test_get_config_options(self):
        oh = OptionsHolder(OPTIONS_PATH, OptionsLoader())

        options = oh.get_config_options()

        self.assertTrue(len(options) > 1, "No options found")
        for n, ioc in options.iteritems():
            self.assertTrue(len(ioc) == 3, "Unexpected details in config")
            self.assertTrue("macros" in ioc)
            self.assertTrue("pvsets" in ioc)
            self.assertTrue("pvs" in ioc)

            self.assertTrue(len(ioc["macros"]) > 1)
            self.assertTrue(len(ioc["pvsets"]) > 1)
            self.assertTrue(len(ioc["pvs"]) > 1)

            for macro in ioc["macros"]:
                self.assertTrue("description" in macro)
                self.assertTrue("pattern" in macro)
            for pvset in ioc["pvsets"]:
                self.assertTrue("description" in pvset)
                self.assertTrue("pattern" not in pvset)
            for pv in ioc["pvs"]:
                self.assertTrue("description" in pv)
                self.assertTrue("pattern" not in pv)

