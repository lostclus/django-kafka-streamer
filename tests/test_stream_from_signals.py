import datetime
from unittest import mock

from kafkastreamer import TYPE_CREATE, TYPE_DELETE, TYPE_UPDATE, stop_handlers
from kafkastreamer.stream import Message, MessageContext, MessageMeta
from tests.testapp.models import ModelA
from tests.utils import patch_now, patch_producer


@patch_producer()
@patch_now()
def test_create(producer_m):
    producer_send_m = producer_m.return_value.send
    assert len(producer_send_m.mock_calls) == 0

    obj = ModelA.objects.create(
        field1=1,
        field2="a",
    )

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-a",
            Message(
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
            ),
            key=None,
        ),
    ]


@patch_producer()
@patch_now()
def test_update(producer_m):
    producer_send_m = producer_m.return_value.send

    with stop_handlers():
        obj = ModelA.objects.create(
            field1=1,
            field2="a",
        )

    assert len(producer_send_m.mock_calls) == 0
    obj.field1 = 2
    obj.save()

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-a",
            Message(
                meta=MessageMeta(
                    timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
                    msg_type=TYPE_UPDATE,
                    context=MessageContext(
                        source="test",
                        user_id=None,
                        extra=None,
                    ),
                ),
                obj_id=obj.pk,
                data={
                    "id": obj.pk,
                    "field1": 2,
                    "field2": "a",
                },
            ),
            key=None,
        ),
    ]


@patch_producer()
@patch_now()
def test_delete(producer_m):
    producer_send_m = producer_m.return_value.send

    with stop_handlers():
        obj = ModelA.objects.create(
            field1=1,
            field2="a",
        )
    obj_id = obj.pk

    assert len(producer_send_m.mock_calls) == 0
    obj.delete()

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-a",
            Message(
                meta=MessageMeta(
                    timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
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
                    "field1": 1,
                    "field2": "a",
                },
            ),
            key=None,
        ),
    ]
