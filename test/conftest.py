"""
Copyright 2018-2019 Splunk, Inc..

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from lib.commonkafka import *
from lib.connect_params import *
from datetime import datetime
from kafka.producer import KafkaProducer
from lib.helper import get_test_folder
from lib.data_gen import generate_connector_content
import pytest
import yaml
import uuid

logging.config.fileConfig(os.path.join(get_test_folder(), "logging.conf"))
logger = logging.getLogger(__name__)

_config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
with open(_config_path, 'r') as yaml_file:
    config = yaml.load(yaml_file)


@pytest.fixture(scope="class")
def setup(request):
    return config


def pytest_configure():
    # Generate message data
    topics = [config["kafka_topic"], config["kafka_topic_2"], config["kafka_header_topic"],
              "test_splunk_hec_malformed_events"]

    create_kafka_topics(config, topics)
    producer = KafkaProducer(bootstrap_servers=config["kafka_broker_url"],
                             value_serializer=lambda v: json.dumps(v).encode('utf-8'))

    for _ in range(3):
        id_1 = str(uuid.uuid1())
        msg = {"timestamp": config['timestamp'], "_id": id_1}
        producer.send(config["kafka_topic"], msg)
        id_2 = str(uuid.uuid1())
        msg_2 = {"timestamp": str(datetime.now()), "_id": id_2}
        producer.send(config["kafka_topic_2"], msg_2)
    #
    #     headers_to_send = [('header_index', b'kafka'), ('header_source_event', b'kafka_header_source_event'),
    #                        ('header_host_event', b'kafkahostevent.com'),
    #                        ('header_sourcetype_event', b'kafka_header_sourcetype_event')]
    #     producer.send(config["kafka_header_topic"], msg, headers=headers_to_send)
    #
    #     headers_to_send = [('header_index', b'kafka'), ('header_source_raw', b'kafka_header_source_raw'),
    #                        ('header_host_raw', b'kafkahostraw.com'),
    #                        ('header_sourcetype_raw', b'kafka_header_sourcetype_raw')]
    #     producer.send(config["kafka_header_topic"], msg, headers=headers_to_send)
    #
    #     headers_to_send = [('splunk.header.index', b'kafka'),
    #                        ('splunk.header.host', b'kafkahost.com'),
    #                        ('splunk.header.source', b'kafka_custom_header_source'),
    #                        ('splunk.header.sourcetype', b'kafka_custom_header_sourcetype')]
    #     producer.send(config["kafka_header_topic"], msg, headers=headers_to_send)
    #
    # producer.send("test_splunk_hec_malformed_events", {})
    # producer.send("test_splunk_hec_malformed_events", {"&&": "null", "message": ["$$$$****////", 123, None]})
    producer.flush()

    # Launch all connectors for tests
    for param in connect_params:
        connector_content = generate_connector_content(param)
        create_kafka_connector(config, connector_content)

    # wait for data to be ingested to Splunk
    time.sleep(200)


def pytest_unconfigure():
    # Delete launched connectors
    for param in connect_params:
        delete_kafka_connector(config, param)
