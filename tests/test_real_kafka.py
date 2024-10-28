import json
import os
from datetime import datetime, timezone

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

    objects = []
    with stop_handlers():
        for i in range(20):
            obj = ModelA.objects.create(field1=i, field2=f"a{i}")
            objects.append(obj)

    streamer = ModelAStreamer(
        partition_key_serializer=partition_key_serializer,
        partitioner=partitioner,
    )
    timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    count = streamer.send_objects(objects, msg_type=TYPE_CREATE, timestamp=timestamp)
    assert count == len(objects)

    consumed_records = list(consumer)
    consumed_data = [json.loads(record.value) for record in consumed_records]
    assert consumed_data == [
        {
            "_time": timestamp.isoformat().replace("+00:00", "Z"),
            "_type": "create",
            "_source": "test",
            "id": obj.pk,
            "field1": i,
            "field2": f"a{i}",
        }
        for i, obj in enumerate(objects)
    ]
