import datetime
from unittest import mock

import pytest

from kafkastreamer import (
    TYPE_CREATE,
    TYPE_DELETE,
    TYPE_ENUMERATE,
    TYPE_EOS,
    stop_handlers,
)
from kafkastreamer.serializers import object_id_key_serializer
from kafkastreamer.stream import Message, MessageContext, MessageMeta
from tests.testapp.models import ModelA, ModelB, ModelC
from tests.testapp.streamers import ModelAStreamer, ModelBStreamer, ModelCStreamer
from tests.utils import patch_producer


def test_constructor():
    streamer = ModelAStreamer(batch_size=100)
    assert streamer.batch_size == 100


def test_get_id():
    obj = ModelA.objects.create(field1=1, field2="a")
    streamer = ModelAStreamer()
    obj_id = streamer.get_id(obj, batch=None)
    assert obj_id == obj.pk


def test_get_data_for_object():
    obj = ModelA.objects.create(field1=1, field2="a")
    streamer = ModelAStreamer()
    data = streamer.get_data_for_object(obj, batch=None)
    assert data == {
        "id": obj.pk,
        "field1": 1,
        "field2": "a",
    }


def test_get_data_for_object_with_custom_field_end_extra():
    obj = ModelB.objects.create(x=1, y=2)
    streamer = ModelBStreamer()
    data = streamer.get_data_for_object(obj, batch=None)
    assert data == {
        "id": obj.pk,
        "x": 1,
        "y": 2,
        "z": 3,
    }


def test_get_data_for_object_with_relation():
    obj1 = ModelA.objects.create(field1=1, field2=2)
    obj2 = ModelB.objects.create(x=1, y=2)
    obj3 = ModelC.objects.create(a=obj1, b=obj2)
    streamer = ModelCStreamer()
    data = streamer.get_data_for_object(obj3, batch=None)
    assert data == {
        "id": obj3.pk,
        "a_id": obj3.a_id,
        "a": {
            "id": obj1.pk,
            "field1": 1,
            "field2": 2,
        },
        "b_id": obj3.b_id,
        "b": {
            "id": obj2.pk,
            "x": 1,
            "y": 2,
        },
    }


def test_get_data_for_object_with_relation_and_exclude():
    obj1 = ModelA.objects.create(field1=1, field2=2)
    obj2 = ModelB.objects.create(x=1, y=2)
    obj3 = ModelC.objects.create(a=obj1, b=obj2)
    streamer = ModelCStreamer(exclude=["a.field2", "b.x"])
    data = streamer.get_data_for_object(obj3, batch=None)
    assert data == {
        "id": obj3.pk,
        "a_id": obj3.a_id,
        "a": {
            "id": obj1.pk,
            "field1": 1,
        },
        "b_id": obj3.b_id,
        "b": {
            "id": obj2.pk,
            "y": 2,
        },
    }


def test_get_message():
    obj = ModelA.objects.create(field1=1, field2="a")
    streamer = ModelAStreamer()
    msg = streamer.get_message(
        obj,
        batch=None,
        msg_type=TYPE_CREATE,
        timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
    )
    assert msg == Message(
        meta=MessageMeta(
            timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
            msg_type=TYPE_CREATE,
            context=MessageContext(
                source="test",
                user_id=None,
                extra=None,
            ),
        ),
        obj_id=obj.pk,
        data={
            "id": obj.pk,
            "field1": 1,
            "field2": "a",
        },
    )


def test_get_message_with_extra_data():
    obj = ModelB.objects.create(x=1, y=2)
    streamer = ModelBStreamer()
    msg = streamer.get_message(
        obj,
        batch=None,
        msg_type=TYPE_CREATE,
        timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
    )
    assert msg == Message(
        meta=MessageMeta(
            timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
            msg_type=TYPE_CREATE,
            context=MessageContext(
                source="test",
                user_id=None,
                extra=None,
            ),
        ),
        obj_id=obj.pk,
        data={
            "id": obj.pk,
            "x": 1,
            "y": 2,
            "z": 3,
            "e": "extra",
        },
    )


def test_get_delete_message():
    obj = ModelA.objects.create(field1=1, field2="a")
    streamer = ModelAStreamer()
    msg = streamer.get_delete_message(
        obj_id=obj.pk,
        timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
        obj=obj,
        batch=None,
    )
    assert msg == Message(
        meta=MessageMeta(
            timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
            msg_type=TYPE_DELETE,
            context=MessageContext(
                source="test",
                user_id=None,
                extra=None,
            ),
        ),
        obj_id=obj.pk,
        data={
            "id": obj.pk,
        },
    )


def test_get_enumerate_message():
    streamer = ModelAStreamer()
    msg = streamer.get_enumerate_message(
        objects_ids=[1, 2, 3],
        timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
        batch=None,
    )
    assert msg == Message(
        meta=MessageMeta(
            timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
            msg_type=TYPE_ENUMERATE,
            context=MessageContext(
                source="test",
                user_id=None,
                extra=None,
            ),
        ),
        obj_id=1,
        data={
            "ids": [1, 2, 3],
        },
    )


def test_get_enumerate_message_with_chunk():
    streamer = ModelAStreamer()
    msg = streamer.get_enumerate_message(
        objects_ids=[1, 2, 3],
        timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
        batch=None,
        chunk_index=3,
        chunk_total=10,
        chunk_session="0000-0001",
    )
    assert msg == Message(
        meta=MessageMeta(
            timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
            msg_type=TYPE_ENUMERATE,
            context=MessageContext(
                source="test",
                user_id=None,
                extra=None,
            ),
        ),
        obj_id=1,
        data={
            "ids": [1, 2, 3],
            "chunk": {
                "index": 3,
                "count": 10,
                "session": "0000-0001",
            },
        },
    )


def test_get_eos_message():
    streamer = ModelAStreamer()
    msg = streamer.get_eos_message(
        timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
    )
    assert msg == Message(
        meta=MessageMeta(
            timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
            msg_type=TYPE_EOS,
            context=MessageContext(
                source="test",
                user_id=None,
                extra=None,
            ),
        ),
        obj_id=None,
        data={},
    )


def test_get_context_info():
    streamer = ModelAStreamer()
    context = streamer.get_context_info()
    assert context == MessageContext(
        source="test",
        user_id=None,
        extra=None,
    )


def test_get_batch_for_objects():
    obj1 = ModelA.objects.create(field1=1, field2="a")
    obj2 = ModelA.objects.create(field1=2, field2="b")
    streamer = ModelAStreamer()
    batch = streamer.get_batch(
        objects=[obj1, obj2],
    )
    assert batch is not None
    assert set(batch.get_objects()) == {obj1, obj2}


def test_get_batch_for_queryset():
    obj1 = ModelA.objects.create(field1=1, field2="a")
    obj2 = ModelA.objects.create(field1=2, field2="b")
    streamer = ModelAStreamer()
    queryset = ModelA.objects.all()
    batch = streamer.get_batch(
        queryset=queryset,
        objects_ids=[obj1.pk, obj2.pk],
    )
    assert batch is not None
    assert set(batch.get_objects()) == {obj1, obj2}


def test_get_batch_for_queryset_with_related():
    obj1 = ModelA.objects.create(field1=1, field2=2)
    obj2 = ModelB.objects.create(x=1, y=2)
    obj3 = ModelC.objects.create(a=obj1, b=obj2)
    streamer = ModelCStreamer()
    queryset = ModelC.objects.all()
    batch = streamer.get_batch(
        queryset=queryset,
        objects_ids=[obj3.pk],
    )
    assert batch is not None
    assert set(batch.get_objects()) == {obj3}


def test_get_batch_for_manager():
    obj1 = ModelA.objects.create(field1=1, field2="a")
    obj2 = ModelA.objects.create(field1=2, field2="b")
    streamer = ModelAStreamer()
    manager = ModelA.objects
    batch = streamer.get_batch(
        manager=manager,
        objects_ids=[obj1.pk, obj2.pk],
    )
    assert batch is not None
    assert set(batch.get_objects()) == {obj1, obj2}


def test_get_messages_for_objects():
    obj1 = ModelA.objects.create(field1=1, field2="a")
    obj2 = ModelA.objects.create(field1=2, field2="b")
    streamer = ModelAStreamer()
    messages = streamer.get_messages_for_objects(
        ModelA.objects,
        msg_type=TYPE_CREATE,
        timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
    )

    assert list(messages) == [
        Message(
            meta=MessageMeta(
                timestamp=datetime.datetime(2023, 1, 1, 0, 0),
                msg_type=TYPE_CREATE,
                context=MessageContext(
                    source="test",
                    user_id=None,
                    extra=None,
                ),
            ),
            obj_id=obj1.pk,
            data={
                "id": obj1.pk,
                "field1": 1,
                "field2": "a",
            },
        ),
        Message(
            meta=MessageMeta(
                timestamp=datetime.datetime(2023, 1, 1, 0, 0),
                msg_type=TYPE_CREATE,
                context=MessageContext(
                    source="test",
                    user_id=None,
                    extra=None,
                ),
            ),
            obj_id=obj2.pk,
            data={
                "id": obj2.pk,
                "field1": 2,
                "field2": "b",
            },
        ),
    ]


def test_get_messages_for_ids_delete():
    streamer = ModelAStreamer()
    messages = streamer.get_messages_for_ids_delete(
        objects_ids=[1, 2, 3],
        timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
        manager=ModelA.objects,
    )

    assert list(messages) == [
        Message(
            meta=MessageMeta(
                timestamp=datetime.datetime(2023, 1, 1, 0, 0),
                msg_type=TYPE_DELETE,
                context=MessageContext(
                    source="test",
                    user_id=None,
                    extra=None,
                ),
            ),
            obj_id=obj_id,
            data={
                "id": obj_id,
            },
        )
        for obj_id in [1, 2, 3]
    ]


@pytest.mark.parametrize("partition_key_serializer", [None, object_id_key_serializer])
@patch_producer()
def test_send_objects(producer_m, partition_key_serializer):
    producer_send_m = producer_m.return_value.send
    assert len(producer_send_m.mock_calls) == 0

    with stop_handlers():
        obj1 = ModelA.objects.create(field1=1, field2="a")
        obj2 = ModelA.objects.create(field1=2, field2="b")

    streamer = ModelAStreamer(partition_key_serializer=partition_key_serializer)
    count = streamer.send_objects(
        ModelA.objects,
        msg_type=TYPE_CREATE,
        timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
    )

    assert count == 2

    msg1 = Message(
        meta=MessageMeta(
            timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
            msg_type=TYPE_CREATE,
            context=MessageContext(
                source="test",
                user_id=None,
                extra=None,
            ),
        ),
        obj_id=obj1.pk,
        data={
            "id": obj1.pk,
            "field1": 1,
            "field2": "a",
        },
    )
    msg2 = Message(
        meta=MessageMeta(
            timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
            msg_type=TYPE_CREATE,
            context=MessageContext(
                source="test",
                user_id=None,
                extra=None,
            ),
        ),
        obj_id=obj2.pk,
        data={
            "id": obj2.pk,
            "field1": 2,
            "field2": "b",
        },
    )

    if partition_key_serializer is None:
        assert producer_send_m.mock_calls == [
            mock.call("model-a", msg1, key=None),
            mock.call("model-a", msg2, key=None),
        ]
    else:
        assert producer_send_m.mock_calls == [
            mock.call("model-a", msg1, key=msg1),
            mock.call("model-a", msg2, key=msg2),
        ]


def test_message_serializer_works():
    streamer = ModelAStreamer()

    msg = Message(
        meta=MessageMeta(
            timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
            msg_type=TYPE_CREATE,
            context=MessageContext(
                source="test",
                user_id=None,
                extra=None,
            ),
        ),
        obj_id=1,
        data={
            "id": 1,
        },
    )

    msg_bytes = streamer.message_serializer(msg)
    assert type(msg_bytes) is bytes
