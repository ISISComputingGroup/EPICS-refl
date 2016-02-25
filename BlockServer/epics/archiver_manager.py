import os
import datetime
import time
import urllib2
from subprocess import Popen
import xml.etree.ElementTree as eTree
from xml.dom import minidom
from server_common.utilities import print_and_log
from archiver_wrapper import ArchiverWrapper


class ArchiverManager(object):
    """This class is responsible for updating the EPICS Archiver that is responsible for logging the blocks."""

    def __init__(self, uploader_path, settings_path, archiver=ArchiverWrapper()):
        """Constructor.

        Args:
            uploader_path (string) : The filepath for the program that uploads the archiver settings
            settings_path (string) : The filepath for the settings to be writen to
        """
        self._uploader_path = uploader_path
        self._settings_path = settings_path
        self._archive_wrapper = archiver

    def update_archiver(self, block_prefix, blocks):
        """Update the archiver to log the blocks specified.

        Args:
            block_prefix (string) : The block prefix
            blocks (list) : The blocks to archive
        """
        try:
            if self._settings_path is not None:
                self._generate_archive_config(block_prefix, blocks)
            if self._uploader_path is not None:
                self._upload_archive_config()
                # Needs a second delay
                time.sleep(1)
                self._archive_wrapper.restart_archiver()
        except Exception as err:
            print_and_log("Could not update archiver: %s" % str(err), "MAJOR")

    def _generate_archive_config(self, block_prefix, blocks):
        print_and_log("Generating archiver configuration file: %s" % self._settings_path)
        root = eTree.Element('engineconfig')
        group = eTree.SubElement(root, 'group')
        name = eTree.SubElement(group, 'name')
        name.text = "BLOCKS"
        for block in blocks:
            # Append prefix for the archiver
            self._generate_archive_channel(group, block_prefix, block)

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

    def _generate_archive_channel(self, group, block_prefix, block):
        # xml not produced for scans of 0 period
        if not (block.log_periodic and block.log_rate == 0):
            channel = eTree.SubElement(group, 'channel')
            name = eTree.SubElement(channel, 'name')
            name.text = block_prefix + block.name
            period = eTree.SubElement(channel, 'period')
            if block.log_periodic:
                period.text = str(datetime.timedelta(seconds=block.log_rate))
                eTree.SubElement(channel, 'scan')
            else:
                period.text = str(datetime.timedelta(seconds=1))
                monitor = eTree.SubElement(channel, 'monitor')
                monitor.text = str(block.log_deadband)