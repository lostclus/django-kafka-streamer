import datetime
from unittest import mock

import pytest

from kafkastreamer import (
    TYPE_CREATE,
    TYPE_DELETE,
    TYPE_ENUMERATE,
    TYPE_EOS,
    TYPE_REFRESH,
    TYPE_UPDATE,
    RefreshFinalizeType,
    full_refresh,
    get_registry,
    get_streamer,
    send,
    send_create,
    send_delete,
    send_refresh,
    send_update,
    squash,
    stop_handlers,
)
from kafkastreamer.stream import Message, MessageContext, MessageMeta
from tests.testapp.models import ModelA
from tests.utils import patch_now, patch_producer


@patch_producer()
@patch_now()
@pytest.mark.parametrize(
    "objects_type",
    ["list", "list_and_manager", "queryset", "manager"],
)
@pytest.mark.parametrize(
    "msg_type",
    [TYPE_CREATE, TYPE_UPDATE, TYPE_DELETE, TYPE_REFRESH],
)
def test_send(producer_m, objects_type, msg_type):
    producer_send_m = producer_m.return_value.send

    with stop_handlers():
        obj = ModelA.objects.create(
            field1=1,
            field2="a",
        )

    assert len(producer_send_m.mock_calls) == 0

    if objects_type == "list":
        count = send([obj], msg_type=msg_type)
    elif objects_type == "list_and_manager":
        count = send([obj], manager=ModelA.objects, msg_type=msg_type)
    elif objects_type == "queryset":
        count = send(ModelA.objects.all(), msg_type=msg_type)
    elif objects_type == "manager":
        count = send(ModelA.objects, msg_type=msg_type)

    assert count == 1
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


def test_send_empty():
    count = send([])
    assert count == 0


@mock.patch("kafkastreamer.registry._registry", new={})
def test_send_unregistered():
    with stop_handlers():
        obj = ModelA.objects.create(
            field1=1,
            field2="a",
        )
    count = send([obj])
    assert count == 0


@patch_producer()
def test_send_with_squash(producer_m):
    producer_send_m = producer_m.return_value.send

    with stop_handlers():
        obj = ModelA.objects.create(
            field1=1,
            field2="a",
        )

    with squash():
        send(
            [obj],
            msg_type=TYPE_UPDATE,
            timestamp=datetime.datetime(2023, 1, 1, 0, 0, 0),
        )
        send(
            [obj],
            msg_type=TYPE_UPDATE,
            timestamp=datetime.datetime(2023, 1, 1, 0, 1, 0),
        )

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-a",
            Message(
                meta=MessageMeta(
                    timestamp=datetime.datetime(2023, 1, 1, 0, 1, 0),
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
                    "field1": 1,
                    "field2": "a",
                },
            ),
            key=None,
        ),
    ]


@patch_producer()
@patch_now()
@pytest.mark.parametrize(
    "msg_type",
    [TYPE_CREATE, TYPE_UPDATE, TYPE_DELETE, TYPE_REFRESH],
)
def test_send_shortcut(producer_m, msg_type):
    producer_send_m = producer_m.return_value.send

    with stop_handlers():
        obj = ModelA.objects.create(
            field1=1,
            field2="a",
        )

    func = {
        TYPE_CREATE: send_create,
        TYPE_UPDATE: send_update,
        TYPE_DELETE: send_delete,
        TYPE_REFRESH: send_refresh,
    }[msg_type]

    func([obj])

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
@pytest.mark.parametrize(
    "refresh_finalize_type",
    [RefreshFinalizeType.ENUMERATE, RefreshFinalizeType.EOS],
)
@pytest.mark.parametrize("model_or_manager", ["model", "manager"])
def test_full_refresh(producer_m, refresh_finalize_type, model_or_manager):
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

    streamer = get_streamer(ModelA)
    orig_refresh_finalize_type = streamer.refresh_finalize_type
    try:
        streamer.refresh_finalize_type = refresh_finalize_type
        if model_or_manager == "model":
            full_refresh(ModelA)
        elif model_or_manager == "manager":
            full_refresh(ModelA.objects)
    finally:
        streamer.refresh_finalize_type = orig_refresh_finalize_type

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
            (
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
                )
                if refresh_finalize_type == RefreshFinalizeType.ENUMERATE
                else Message(
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
            ),
            key=None,
        ),
    ]


@patch_producer()
@patch_now()
def test_full_refresh_all_registered(producer_m):
    producer_send_m = producer_m.return_value.send

    assert len(producer_send_m.mock_calls) == 0

    full_refresh()

    assert len(producer_send_m.mock_calls) == len(get_registry())
