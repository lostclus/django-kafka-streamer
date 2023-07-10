import os

import pytest
from django.conf import settings
from django.test.utils import override_settings
from kafka import KafkaConsumer

from kafkastreamer import TYPE_CREATE, stop_handlers
from kafkastreamer.partitioners import modulo_partitioner
from kafkastreamer.serializers import object_id_key_serializer
from tests.testapp.models import ModelA
from tests.testapp.streamers import ModelAStreamer


@pytest.fixture
def bootstrap_servers():
    servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS").split(",")
    new_conf = {**settings.KAFKA_STREAMER, "BOOTSTRAP_SERVERS": servers}
    with override_settings(KAFKA_STREAMER=new_conf):
        yield servers


@pytest.mark.realkafka
@pytest.mark.parametrize(
    ("partition_key_serializer", "partitioner"),
    [
        (None, None),
        (object_id_key_serializer, None),
        (object_id_key_serializer, modulo_partitioner),
    ],
)
def test_produce_consume(bootstrap_servers, partition_key_serializer, partitioner):
    consumer = KafkaConsumer(
        "model-a",
        group_id="test",
        bootstrap_servers=bootstrap_servers,
        consumer_timeout_ms=10,
    )
    assert list(consumer) == []

    with stop_handlers():
        obj = ModelA.objects.create(field1=1, field2="a")
    streamer = ModelAStreamer(
        partition_key_serializer=partition_key_serializer,
        partitioner=partitioner,
    )
    count = streamer.send_objects([obj], msg_type=TYPE_CREATE)
    assert count == 1

    assert len(list(consumer)) > 0
