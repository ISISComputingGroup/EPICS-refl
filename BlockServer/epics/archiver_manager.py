import os
import datetime
import time
import urllib2
from subprocess import Popen
import xml.etree.ElementTree as eTree
from xml.dom import minidom
from server_common.utilities import print_and_log


class ArchiverManager(object):
    """This class is responsible for updating the EPICS Archiver that is responsible for logging the blocks"""

    def __init__(self, uploader_path, settings_path, test_mode=False):
        self._uploader_path = uploader_path
        self._settings_path = settings_path
        self._test_mode = test_mode

    def set_testing_mode(self, test_mode):
        self._test_mode = test_mode

    def update_archiver(self, block_prefix, blocks):
        if self._test_mode:
            return
        try:
            if self._settings_path is not None:
                self.generate_archive_config(block_prefix, blocks)
            if self._uploader_path is not None:
                self._upload_archive_config()
                # Needs a second delay
                time.sleep(1)
                self._restart_archiver()
        except Exception as err:
            print_and_log("Could not update archiver: %s" % str(err), "ERROR")

    def _restart_archiver(self):
        if self._test_mode:
            return
        # Set to ignore proxy for localhost
        proxy_handler = urllib2.ProxyHandler({})
        opener = urllib2.build_opener(proxy_handler)
        urllib2.install_opener(opener)
        urllib2.urlopen("http://localhost:4813/restart")

    def generate_archive_config(self, block_prefix, blocks):
        print_and_log("Generating archiver configuration file: %s" % self._settings_path)
        root = eTree.Element('engineconfig')
        group = eTree.SubElement(root, 'group')
        name = eTree.SubElement(group, 'name')
        name.text = "BLOCKS"
        for bname in blocks:
            # Append prefix for the archiver
            blkname = block_prefix + bname
            self._generate_archive_channel(group, blkname)

        with open(self._settings_path, 'w') as f:
            xml = minidom.parseString(eTree.tostring(root)).toprettyxml()
            f.write(xml)

    def _upload_archive_config(self):
        f = os.path.abspath(self._uploader_path)
        if os.path.isfile(f):
            print_and_log("Running archiver settings uploader: %s" % f)
            Popen(f)
        else:
            print_and_log("Could not find specified archiver uploader batch file: %s" % self._uploader_path)

    def _generate_archive_channel(self, group, pv, period_secs=5, monitor=True):
        channel = eTree.SubElement(group, 'channel')
        name = eTree.SubElement(channel, 'name')
        name.text = pv
        period = eTree.SubElement(channel, 'period')
        period.text = str(datetime.timedelta(seconds=period_secs))
        if monitor:
            eTree.SubElement(channel, 'monitor')