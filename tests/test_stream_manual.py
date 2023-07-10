import datetime
from unittest import mock

import pytest

from kafkastreamer import (
    TYPE_ENUMERATE,
    TYPE_REFRESH,
    full_refresh,
    send,
    stop_handlers,
)
from kafkastreamer.stream import Message, MessageContext, MessageMeta
from tests.testapp.models import ModelA
from tests.utils import patch_now, patch_producer


@patch_producer()
@patch_now()
@pytest.mark.parametrize(
    "msg_type",
    ["create", "update", "delete", "refresh"],
)
def test_send(producer_m, msg_type):
    producer_send_m = producer_m.return_value.send

    with stop_handlers():
        obj = ModelA.objects.create(
            field1=1,
            field2="a",
        )

    assert len(producer_send_m.mock_calls) == 0

    send([obj], msg_type=msg_type)

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-a",
            Message(
                meta=MessageMeta(
                    timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
                    msg_type=msg_type,
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
def test_full_refresh(producer_m):
    producer_send_m = producer_m.return_value.send

    with stop_handlers():
        obj1 = ModelA.objects.create(
            field1=1,
            field2="a",
        )
        obj2 = ModelA.objects.create(
            field1=2,
            field2="b",
        )

    assert len(producer_send_m.mock_calls) == 0

    full_refresh(ModelA)

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-a",
            Message(
                meta=MessageMeta(
                    timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
                    msg_type=TYPE_REFRESH,
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
            key=None,
        ),
        mock.call(
            "model-a",
            Message(
                meta=MessageMeta(
                    timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
                    msg_type=TYPE_REFRESH,
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
            key=None,
        ),
        mock.call(
            "model-a",
            Message(
                meta=MessageMeta(
                    timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
                    msg_type=TYPE_ENUMERATE,
                    context=MessageContext(
                        source="test",
                        user_id=None,
                        extra=None,
                    ),
                ),
                obj_id=obj1.pk,
                data={
                    "ids": [obj1.pk, obj2.pk],
                },
            ),
            key=None,
        ),
    ]
