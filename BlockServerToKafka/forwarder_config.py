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
import json


class ForwarderConfig():
    """ Class that converts the pv information to a forwarder config.
    """
    def __init__(self, topic, using_v4=False, schema="f142"):
        self.schema = schema
        self.topic = topic
        self.using_v4 = using_v4

    def _get_converter(self):
        return {"schema": self.schema, "topic": self.topic}

    def _create_stream(self, blk):
        return {
            "channel": blk,
            "converter": self._get_converter(),
            "channel_provider_type": "pva" if self.using_v4 else "ca"
        }

    def create_forwarder_configuration(self, pvs):
        output_dict = {
            "cmd": "add",
            "streams": [self._create_stream(pv) for pv in pvs]
        }
        return json.dumps(output_dict)

    def remove_forwarder_configuration(self, pvs):
        output_list = []
        for pv in pvs:
            out_dict = {
                "cmd": "stop_channel",
                "channel": pv
            }
            output_list.append(json.dumps(out_dict))
        return output_list
