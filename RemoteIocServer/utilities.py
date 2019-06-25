from __future__ import print_function, unicode_literals, division, absolute_import

import functools
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from server_common.utilities import print_and_log as _common_print_and_log

__all__ = ['print_and_log']

print_and_log = functools.partial(_common_print_and_log, src="REMIOC")
