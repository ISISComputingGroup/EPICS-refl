from server_common.utilities import compress_and_hex
import json

DISALLOWED_BLOCK_NAMES = ["lowlimit", "highlimit", "runcontrol", "wait"]
ALLOWED_BLOCK_REGEX = r"^[a-zA-Z]\w*$"
BLOCK_RULES_PV = "BLOCK_RULES"

class BlockRules(object):
    """Class for managing exposing the rules for allowed block names"""

    def __init__(self, cas):
        """Constructor.

        Args:
            cas (CAServer) : The channel access server for creating PVs on-the-fly
        """
        self._cas = cas
        self._create_pv()

    def _create_pv(self):
        data = {"disallowed": DISALLOWED_BLOCK_NAMES, "regex": ALLOWED_BLOCK_REGEX}
        self._cas.updatePV(BLOCK_RULES_PV, compress_and_hex(json.dumps(data)))
