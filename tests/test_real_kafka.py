import os

import pytest
from django.conf import settings
from django.test.utils import override_settings
from kafka import KafkaConsumer

from kafkastreamer import TYPE_CREATE, stop_handlers
from tests.testapp.models import ModelA
from tests.testapp.streamers import ModelAStreamer


@pytest.fixture
def bootstrap_servers():
    servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS").split(",")
    new_conf = {**settings.KAFKA_STREAMER, "BOOTSTRAP_SERVERS": servers}
    with override_settings(KAFKA_STREAMER=new_conf):
        yield servers


@pytest.mark.realkafka
def test_produce_consume(bootstrap_servers):
    with stop_handlers():
        obj = ModelA.objects.create(field1=1, field2="a")
    streamer = ModelAStreamer()
    count = streamer.send_objects([obj], msg_type=TYPE_CREATE)
    assert count == 1

    consumer = KafkaConsumer(
        "model-a",
        group_id="test",
        bootstrap_servers=bootstrap_servers,
        consumer_timeout_ms=10,
    )
    messages = list(consumer)
    assert len(messages) >= 1
