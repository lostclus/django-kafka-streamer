import datetime
from unittest import mock

from kafkastreamer import TYPE_CREATE, TYPE_DELETE, TYPE_UPDATE, stop_handlers
from kafkastreamer.stream import Message, MessageContext, MessageMeta
from tests.testapp.models import ModelA, ModelD, ModelE, ModelF, ModelG
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
def test_create_with_one_to_many_relation(producer_m):
    producer_send_m = producer_m.return_value.send
    assert len(producer_send_m.mock_calls) == 0

    with stop_handlers():
        d = ModelD.objects.create(field1=1)

    e = ModelE.objects.create(d=d)

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-e",
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
                obj_id=e.pk,
                data={
                    "id": e.pk,
                    "d_id": d.pk,
                    "d": {
                        "id": d.pk,
                        "field1": 1,
                    },
                },
            ),
            key=None,
        ),
        mock.call(
            "model-d",
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
                obj_id=d.pk,
                data={
                    "id": d.pk,
                    "field1": 1,
                    "e_set": [
                        {
                            "id": e.pk,
                            "d_id": d.pk,
                        },
                    ],
                    "f": None,
                },
            ),
            key=None,
        ),
    ]


@patch_producer()
@patch_now()
def test_create_with_one_to_one_relation(producer_m):
    producer_send_m = producer_m.return_value.send
    assert len(producer_send_m.mock_calls) == 0

    with stop_handlers():
        d = ModelD.objects.create(field1=1)

    f = ModelF.objects.create(d=d)

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-f",
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
                obj_id=f.pk,
                data={
                    "id": f.pk,
                    "d_id": d.pk,
                    "d": {
                        "id": d.pk,
                        "field1": 1,
                    },
                },
            ),
            key=None,
        ),
        mock.call(
            "model-d",
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
                obj_id=d.pk,
                data={
                    "id": d.pk,
                    "field1": 1,
                    "e_set": [],
                    "f": {
                        "id": f.pk,
                        "d_id": d.pk,
                    },
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
def test_update_with_one_to_many_relation(producer_m):
    producer_send_m = producer_m.return_value.send
    assert len(producer_send_m.mock_calls) == 0

    with stop_handlers():
        d = ModelD.objects.create(field1=1)
        e = ModelE.objects.create(d=d)

    d.field1 = 2
    d.save()

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-d",
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
                obj_id=d.pk,
                data={
                    "id": d.pk,
                    "field1": 2,
                    "e_set": [
                        {
                            "id": e.pk,
                            "d_id": d.pk,
                        },
                    ],
                    "f": None,
                },
            ),
            key=None,
        ),
        mock.call(
            "model-e",
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
                obj_id=e.pk,
                data={
                    "id": e.pk,
                    "d_id": d.pk,
                    "d": {
                        "id": d.pk,
                        "field1": 2,
                    },
                },
            ),
            key=None,
        ),
    ]


@patch_producer()
@patch_now()
def test_update_with_one_to_one_relation(producer_m):
    producer_send_m = producer_m.return_value.send
    assert len(producer_send_m.mock_calls) == 0

    with stop_handlers():
        d = ModelD.objects.create(field1=1)
        f = ModelF.objects.create(d=d)

    d.field1 = 2
    d.save()

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-d",
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
                obj_id=d.pk,
                data={
                    "id": d.pk,
                    "field1": 2,
                    "e_set": [],
                    "f": {
                        "id": f.pk,
                        "d_id": d.pk,
                    },
                },
            ),
            key=None,
        ),
        mock.call(
            "model-f",
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
                obj_id=f.pk,
                data={
                    "id": f.pk,
                    "d_id": d.pk,
                    "d": {
                        "id": d.pk,
                        "field1": 2,
                    },
                },
            ),
            key=None,
        ),
    ]


@patch_producer()
@patch_now()
def test_update_with_many_to_many_relation(producer_m):
    producer_send_m = producer_m.return_value.send

    with stop_handlers():
        d = ModelD.objects.create(field1=1)
        g = ModelG.objects.create()
        g.d_set.add(d)

    assert len(producer_send_m.mock_calls) == 0
    d.field1 = 2
    d.save()

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-d",
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
                obj_id=d.pk,
                data={
                    "id": d.pk,
                    "field1": 2,
                    "e_set": [],
                    "f": None,
                },
            ),
            key=None,
        ),
        mock.call(
            "model-g",
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
                obj_id=g.pk,
                data={
                    "id": g.pk,
                    "d_set": [
                        {
                            "id": d.pk,
                            "field1": 2,
                        }
                    ],
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


@patch_producer()
@patch_now()
def test_delete_with_one_to_many_relation(producer_m):
    producer_send_m = producer_m.return_value.send

    with stop_handlers():
        d = ModelD.objects.create(field1=1)
        e = ModelE.objects.create(d=d)

    assert len(producer_send_m.mock_calls) == 0
    e_id = e.pk
    e.delete()

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-e",
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
                obj_id=e_id,
                data={
                    "id": e_id,
                    "d_id": d.pk,
                    "d": {
                        "id": d.pk,
                        "field1": 1,
                    },
                },
            ),
            key=None,
        ),
        mock.call(
            "model-d",
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
                obj_id=d.pk,
                data={
                    "id": d.pk,
                    "field1": 1,
                    "e_set": [],
                    "f": None,
                },
            ),
            key=None,
        ),
    ]


@patch_producer()
@patch_now()
def test_delete_with_one_to_one_relation(producer_m):
    producer_send_m = producer_m.return_value.send

    with stop_handlers():
        d = ModelD.objects.create(field1=1)
        f = ModelF.objects.create(d=d)

    assert len(producer_send_m.mock_calls) == 0
    f_id = f.pk
    f.delete()

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-f",
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
                obj_id=f_id,
                data={
                    "id": f_id,
                    "d_id": d.pk,
                    "d": {
                        "id": d.pk,
                        "field1": 1,
                    },
                },
            ),
            key=None,
        ),
        mock.call(
            "model-d",
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
                obj_id=d.pk,
                data={
                    "id": d.pk,
                    "field1": 1,
                    "e_set": [],
                    "f": None,
                },
            ),
            key=None,
        ),
    ]


@patch_producer()
@patch_now()
def test_delete_with_many_to_many_relation(producer_m):
    producer_send_m = producer_m.return_value.send

    with stop_handlers():
        d = ModelD.objects.create(field1=1)
        g = ModelG.objects.create()
        g.d_set.add(d)

    assert len(producer_send_m.mock_calls) == 0
    d_id = d.pk
    d.delete()

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-d",
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
                obj_id=d_id,
                data={
                    "id": d_id,
                    "field1": 1,
                    "e_set": [],
                    "f": None,
                },
            ),
            key=None,
        ),
        mock.call(
            "model-g",
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
                obj_id=g.pk,
                data={
                    "id": g.pk,
                    "d_set": [],
                },
            ),
            key=None,
        ),
    ]


@patch_producer()
@patch_now()
def test_many_to_many_add(producer_m):
    producer_send_m = producer_m.return_value.send
    assert len(producer_send_m.mock_calls) == 0

    with stop_handlers():
        d = ModelD.objects.create(field1=1)
        g = ModelG.objects.create()

    g.d_set.add(d)

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-g",
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
                obj_id=g.pk,
                data={
                    "id": g.pk,
                    "d_set": [
                        {
                            "id": d.pk,
                            "field1": 1,
                        },
                    ],
                },
            ),
            key=None,
        ),
    ]


@patch_producer()
@patch_now()
def test_many_to_many_remove(producer_m):
    producer_send_m = producer_m.return_value.send
    assert len(producer_send_m.mock_calls) == 0

    with stop_handlers():
        d = ModelD.objects.create(field1=1)
        g = ModelG.objects.create()
        g.d_set.add(d)

    g.d_set.remove(d)

    assert producer_send_m.mock_calls == [
        mock.call(
            "model-g",
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
                obj_id=g.pk,
                data={
                    "id": g.pk,
                    "d_set": [],
                },
            ),
            key=None,
        ),
    ]
