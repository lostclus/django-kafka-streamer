import datetime
import json
from decimal import Decimal

import pytest

from kafkastreamer import (
    TYPE_UPDATE,
    flat_json_message_serializer,
    object_id_key_serializer,
)
from kafkastreamer.serializers import DEFAULT_ENCODING
from kafkastreamer.stream import Message, MessageContext, MessageMeta


@pytest.fixture
def message():
    return Message(
        meta=MessageMeta(
            timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
            msg_type=TYPE_UPDATE,
            context=MessageContext(
                source="source",
                user_id=3,
                extra={"foo": "bar"},
            ),
        ),
        obj_id=1,
        data={
            "f_int": 123,
            "f_float": 1234.5,
            "f_decimal": Decimal("123.45"),
            "f_str": "a",
            "f_datetime": datetime.datetime(2023, 1, 2, 12, 30),
            "f_date": datetime.date(2023, 1, 3),
            "f_timedelta": datetime.timedelta(hours=2),
        },
    )


def test_flat_json_message_serializer(message):
    message_bytes = flat_json_message_serializer(message)
    message_data = json.loads(message_bytes.decode(DEFAULT_ENCODING))

    assert message_data == {
        "_time": "2023-01-01T00:00:00",
        "_type": "update",
        "_source": "source",
        "_user_id": 3,
        "_foo": "bar",
        "id": 1,
        "f_int": 123,
        "f_float": 1234.5,
        "f_decimal": "123.45",
        "f_str": "a",
        "f_datetime": "2023-01-02T12:30:00",
        "f_date": "2023-01-03",
        "f_timedelta": "P0DT02H00M00S",
    }


def test_object_id_key_serializer(message):
    key_bytes = object_id_key_serializer(message)
    assert key_bytes == b"1"
    key_bytes = object_id_key_serializer(message._replace(obj_id=None))
    assert key_bytes == b"0"
