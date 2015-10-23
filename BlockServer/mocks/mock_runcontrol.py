from BlockServer.core.constants import TAG_RC_LOW, TAG_RC_HIGH, TAG_RC_ENABLE, TAG_RC_OUT_LIST


class MockBlock(object):
    def __init__(self):
        self.value = 0
        self.enable = False
        self.lowlimit = 0
        self.highlimit = 0


class MockRunControlManager(object):
    def __init__(self):
        self._prefix = ""
        self._block_prefix = ""
        self._stored_settings = None
        self.mock_blocks = dict()

    def update_runcontrol_blocks(self, blocks):
        for b, blk in blocks.iteritems():
            self.mock_blocks[blk.name] = MockBlock()
            self.mock_blocks[blk.name].enable = blk.rc_enabled
            self.mock_blocks[blk.name].lowlimit = blk.rc_lowlimit
            self.mock_blocks[blk.name].highlimit = blk.rc_highlimit

    def get_out_of_range_pvs(self):
        raw = ""
        for n, blk in self.mock_blocks.iteritems():
            if blk.enable:
                if blk.value < blk.lowlimit or blk.value > blk.highlimit:
                    raw += n + " "
        raw = raw.strip().split(" ")
        if raw is not None and len(raw) > 0:
            ans = list()
            for i in raw:
                if len(i) > 0:
                    ans.append(i)
            return ans
        else:
            return []

    def get_current_settings(self, blocks):
        # Blocks object is ignored for testing
        settings = dict()
        for bn, blk in self.mock_blocks.iteritems():
            low = self.mock_blocks[bn].lowlimit
            high = self.mock_blocks[bn].highlimit
            enable = self.mock_blocks[bn].enable
            settings[bn] = {"LOW": low, "HIGH": high, "ENABLE": enable}
        return settings

    def restore_config_settings(self, blocks):
        for n, blk in blocks.iteritems():
            settings = dict()
            if blk.rc_enabled:
                settings["ENABLE"] = True
            if blk.rc_lowlimit is not None:
                settings["LOW"] = blk.rc_lowlimit
            if blk.rc_highlimit is not None:
                settings["LOW"] = blk.rc_highlimit
            self.set_runcontrol_settings(settings)

    def set_runcontrol_settings(self, data):
        # Data should be a dictionary of dictionaries
        for bn, settings in data.iteritems():
            if settings is not None and bn in self.mock_blocks.keys():
                self.mock_blocks[bn].enable = settings["ENABLE"]
                self.mock_blocks[bn].lowlimit = settings["LOW"]
                self.mock_blocks[bn].highlimit = settings["HIGH"]

    def wait_for_ioc_restart(self):
        pass

    def wait_for_ioc_start(self):
        pass

    def start_ioc(self):
        pass

    def restart_ioc(self, clear_autosave):
        pass