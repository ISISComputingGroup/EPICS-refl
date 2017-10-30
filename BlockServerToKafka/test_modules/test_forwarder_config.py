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

import unittest
import json

from BlockServerToKafka.forwarder_config import ForwarderConfig


class TestForwarderConfig(unittest.TestCase):
    test_schema = "schema"
    test_topic = "topic"
    test_block_1 = "block1"
    test_block_2 = "block2"

    def is_json(self, json_str):
        try:
            json.loads(json_str)
        except ValueError:
            return False
        return True

    def setUp(self):
        self.kafka_forwarder = ForwarderConfig(self.test_topic, False, self.test_schema)
        self.config_with_one_block = [self.test_block_1]
        self.config_with_two_blocks = [self.test_block_1, self.test_block_2]

    def test_WHEN_new_forwarder_config_created_THEN_returns_valid_JSON(self):
        output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        self.assertTrue(self.is_json(output))

    def test_WHEN_new_forwarder_config_created_THEN_returns_JSON_containing_add_command(self):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        output = json.loads(raw_output)
        self.assertTrue("cmd" in output)
        self.assertEqual("add", output["cmd"])

    def test_WHEN_new_forwarder_config_created_THEN_returns_JSON_containing_list_of_streams(self):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        output = json.loads(raw_output)
        self.assertTrue("streams" in output)
        self.assertEqual(list, type(output["streams"]))

    def test_WHEN_new_forwarder_config_created_THEN_returns_JSON_containing_streams_with_channels_and_converters(self):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        output = json.loads(raw_output)
        self.assertNotEqual(0, len(output["streams"]))
        for stream in output["streams"]:
            self.assertEqual(dict, type(stream))
            self.assertTrue("channel" in stream)
            self.assertTrue("converter" in stream)

    def test_GIVEN_schema_and_topic_WHEN_forwarder_config_created_THEN_returns_JSON_containing_schema_and_topic(self):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        output = json.loads(raw_output)
        self.assertNotEqual(0, len(output["streams"]))
        for stream in output["streams"]:
            self.assertNotEqual(len(stream["converter"]), 0)
            self.assertTrue("schema" in stream["converter"])
            self.assertTrue("topic" in stream["converter"])
            self.assertEqual(self.test_schema, stream["converter"]["schema"])
            self.assertEqual(self.test_topic, stream["converter"]["topic"])

    def test_GIVEN_using_version_3_WHEN_new_forwarder_config_created_THEN_returns_JSON_containing_streams_with_ca_as_channel_type(self):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        output = json.loads(raw_output)
        self.assertNotEqual(0, len(output["streams"]))
        for stream in output["streams"]:
            self.assertTrue("channel_provider_type" in stream)
            self.assertEqual("ca", stream["channel_provider_type"])

    def test_GIVEN_using_version_4_WHEN_new_forwarder_config_created_THEN_returns_JSON_containing_streams_with_no_channel_type(self):
        kafka_version_4 = ForwarderConfig(self.test_schema, self.test_topic, True)
        raw_output = kafka_version_4.create_forwarder_configuration(self.config_with_one_block)
        output = json.loads(raw_output)
        self.assertNotEqual(0, len(output["streams"]))
        for stream in output["streams"]:
            self.assertFalse("channel_provider_type" in stream)

    def test_GIVEN_configuration_with_one_block_WHEN_new_forwarder_config_created_THEN_returns_JSON_containing_one_stream(self):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        output = json.loads(raw_output)
        self.assertEqual(1, len(output["streams"]))

    def test_GIVEN_configuration_with_two_block_WHEN_new_forwarder_config_created_THEN_returns_JSON_containing_two_stream(self):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_two_blocks)
        output = json.loads(raw_output)
        self.assertEqual(2, len(output["streams"]))

    def test_GIVEN_configuration_with_one_block_WHEN_new_forwarder_config_created_THEN_returns_block_pv_string(self):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        output = json.loads(raw_output)
        stream = output["streams"][0]
        self.assertEqual(self.test_block_1, stream["channel"])

    def test_GIVEN_configuration_with_two_blocks_WHEN_new_forwarder_config_created_THEN_returns_both_block_pv_string(self):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_two_blocks)
        output = json.loads(raw_output)

        for i, blk in enumerate([self.test_block_1, self.test_block_2]):
            stream = output["streams"][i]
            self.assertEqual(blk, stream["channel"])

    def test_WHEN_removed_old_forwarder_THEN_JSON_returns_valid(self):
        output = self.kafka_forwarder.remove_forwarder_configuration(self.config_with_one_block)
        for js in output:
            self.assertTrue(self.is_json(js))

    def test_WHEN_removed_old_forwarder_THEN_returns_JSON_containing_stop_channel_command(self):
        raw_output = self.kafka_forwarder.remove_forwarder_configuration(self.config_with_one_block)
        for js in raw_output:
            output = json.loads(js)
            self.assertTrue("cmd" in output)
            self.assertEqual("stop_channel", output["cmd"])

    def test_GIVEN_configuration_with_one_block_WHEN_removed_old_forwarder_THEN_returns_JSON_containing_block_pv_string(self):
        raw_output = self.kafka_forwarder.remove_forwarder_configuration(self.config_with_one_block)
        self.assertTrue(len(raw_output) == 1)
        for js in raw_output:
            output = json.loads(js)
            self.assertTrue("channel" in output)
            self.assertEqual(self.test_block_1, output["channel"])

    def test_GIVEN_configuration_with_two_blocks_WHEN_removed_old_forwarder_THEN_returns_JSON_containing_both_block_pv_string(self):
        raw_output = self.kafka_forwarder.remove_forwarder_configuration(self.config_with_two_blocks)
        self.assertTrue(len(raw_output) == 2)

        for i, blk in enumerate([self.test_block_1, self.test_block_2]):
            output = json.loads(raw_output[i])
            self.assertTrue("channel" in output)
            self.assertEqual(blk, output["channel"])
