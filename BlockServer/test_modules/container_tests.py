import unittest
from config.containers import IOC


class TestContainersSequence(unittest.TestCase):
    def test_ioc_to_dict(self):
        ioc = IOC("SIMPLE1")
        macros = {"macro1": {'value': 123}, "macro2": {'value': "Hello"}}
        ioc.macros = macros

        d = ioc.to_dict()
        self.assertTrue("name" in d)
        self.assertTrue("macros" in d)
        macrotest = {"name" : "macro1", "value" : 123}
        self.assertTrue(macrotest in d["macros"])
        macrotest = {"name" : "macro2", "value" : "Hello"}
        self.assertTrue(macrotest in d["macros"])
