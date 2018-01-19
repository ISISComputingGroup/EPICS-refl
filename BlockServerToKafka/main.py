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
import sys
sys.path.insert(0, os.path.abspath(os.getcwd()))
from argparse import ArgumentParser
from BlockServerToKafka.block_server_monitor import BlockServerMonitor
from time import sleep
from os import environ
from BlockServerToKafka.kafka_producer import Producer

if __name__ == '__main__':
    parser = ArgumentParser()

    parser.add_argument('-d', '--data', help='Kafka topic to send PV data to', nargs=1, type=str,
                        default='test_bs_forwarder')
    parser.add_argument('-c', '--config', help='Kafka topic to send forwarder config to', nargs=1, type=str,
                        default='test_bs_forwarder_config')
    parser.add_argument('-b', '--broker', help='Location of the Kafka brokers (host:port)', nargs='+', type=str,
                        default='sakura.isis.cclrc.ac.uk:9092')
    parser.add_argument('-p', '--pvprefix', help='PV Prefix of the block server', nargs=1, type=str,
                        default=environ["MYPVPREFIX"])

    args = parser.parse_args()
    KAFKA_DATA = args.data[0]
    KAFKA_CONFIG = args.config[0]
    KAFKA_BROKER = args.broker
    PREFIX = args.pvprefix[0]
    producer = Producer(KAFKA_BROKER, KAFKA_CONFIG, KAFKA_DATA)
    monitor = BlockServerMonitor("{}CS:BLOCKSERVER:BLOCKNAMES".format(PREFIX), PREFIX, producer)

    while True:
        sleep(0.1)
