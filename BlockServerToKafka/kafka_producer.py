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
from forwarder_config import ForwarderConfig
from kafka import KafkaProducer, errors, SimpleClient
from server_common.utilities import print_and_log


class Producer:
    """
    A wrapper class for the kafka producer.
    """

    def __init__(self, server, config_topic, data_topic):
        self.topic = config_topic
        self.producer, self.client = self.set_up_producer(server)
        self.converter = ForwarderConfig(data_topic)

    def set_up_producer(self, server):
        try:
            client = SimpleClient(server)
            producer = KafkaProducer(bootstrap_servers=server)
        except errors.NoBrokersAvailable:
            print_and_log("No brokers found on server: " + server[0])
            quit()
        except errors.ConnectionError:
            print_and_log("No server found, connection error")
            quit()
        except errors.InvalidConfigurationError:
            print_and_log("Invalid configuration")
            quit()
        except errors.InvalidTopicError:
            print_and_log("Invalid topic, to enable auto creation of topics set"
                          " auto.create.topics.enable to false in broker configuration")
        return producer, client

    def add_config(self, pvs):
        """
        Creates a forwarder configuration to add more pvs to be monitored.

        Args:
             pvs (list): A list of new PVs to add to the forwarder configuration.

        Returns:
            None.
        """
        if not self.topic_exists(self.topic):
            print_and_log("WARNING: topic {} does not exist. It will be created by default.".format(self.topic))
        data = self.converter.create_forwarder_configuration(pvs)
        print_and_log("Sending data {}".format(data))
        self.producer.send(self.topic, bytes(data))

    def topic_exists(self, topicname):
        return self.client.ensure_topic_exists(topicname)

    def remove_config(self, pvs):
        """
        Creates a forwarder configuration to remove pvs that are being monitored.

        Args:
            pvs (list): A list of PVs to remove from the forwarder configuration.

        Returns:
            None.
        """

        data = self.converter.remove_forwarder_configuration(pvs)
        for pv in data:
            print_and_log("Sending data {}".format(data))
            self.producer.send(self.topic, bytes(pv))
