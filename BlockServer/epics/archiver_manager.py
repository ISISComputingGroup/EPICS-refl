# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php

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
            uploader_path (string): The filepath for the program that uploads the archiver settings.
            settings_path (string): The filepath for the settings to be writen to.
            archiver (ArchiverWrapper): The instance used to access the Archiver.
        """
        self._uploader_path = uploader_path
        self._settings_path = settings_path
        self._archive_wrapper = archiver

    def update_archiver(self, block_prefix, blocks):
        """Update the archiver to log the blocks specified.

        Args:
            block_prefix (string): The block prefix
            blocks (list): The blocks to archive
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
        dataweb = eTree.SubElement(root, 'group')
        dataweb_name = eTree.SubElement(dataweb, 'name')
        dataweb_name.text = "DATAWEB"
        for block in blocks:
            # Append prefix for the archiver
            self._generate_archive_channel(group, block_prefix, block, dataweb)

        with open(self._settings_path, 'w') as f:
            xml = minidom.parseString(eTree.tostring(root)).toprettyxml()
            f.write(xml)

    def _upload_archive_config(self):
        f = os.path.abspath(self._uploader_path)
        if os.path.isfile(f):
            print_and_log("Running archiver settings uploader: %s" % f)
            p = Popen(f)
            p.wait()
        else:
            print_and_log("Could not find specified archiver uploader batch file: %s" % self._uploader_path)

    def _generate_archive_channel(self, group, block_prefix, block, dataweb):
        if not (block.log_periodic and block.log_rate == 0):
            # Blocks that are logged
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
        else:
            # Blocks that aren't logged, but are needed for the dataweb view
            channel = eTree.SubElement(dataweb, 'channel')
            name = eTree.SubElement(channel, 'name')
            name.text = block_prefix + block.name
            period = eTree.SubElement(channel, 'period')
            period.text = str(datetime.timedelta(seconds=300))
            eTree.SubElement(channel, 'scan')
