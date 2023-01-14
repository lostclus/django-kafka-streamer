from unittest import mock

from django.conf import settings
from django.test.utils import override_settings

from kafkastreamer import set_context, squash, stop_handlers
from tests.testapp.models import ModelA
from tests.testapp.streamers import ModelAStreamer
from tests.utils import patch_producer


@override_settings(
    KAFKA_STREAMER={
        **settings.KAFKA_STREAMER,
        "DEFAULT_SOURCE": "default-source",
    },
)
def test_set_context_source():
    streamer = ModelAStreamer()

    assert streamer.get_context_info().source == "default-source"
    with set_context(source="custom-source"):
        assert streamer.get_context_info().source == "custom-source"
    assert streamer.get_context_info().source == "default-source"


def test_set_context_user():
    streamer = ModelAStreamer()
    user = mock.MagicMock()
    user.is_authenticated.return_value = True
    user.pk = 12345

    assert streamer.get_context_info().user_id is None
    with set_context(user=user):
        assert streamer.get_context_info().user_id == 12345
    assert streamer.get_context_info().user_id is None


@patch_producer()
def test_stop_handlers(producer_m):
    producer_send_m = producer_m.return_value.send
    assert len(producer_send_m.mock_calls) == 0

    with stop_handlers():
        ModelA.objects.create(field1=1, field2=2)

    assert len(producer_send_m.mock_calls) == 0


@patch_producer()
def test_squash_create_update(producer_m):
    producer_send_m = producer_m.return_value.send
    assert len(producer_send_m.mock_calls) == 0

    with squash():
        obj = ModelA.objects.create(field1=1, field2=2)
        obj.field1 = 2
        obj.save()

    assert len(producer_send_m.mock_calls) == 1

    msg = producer_send_m.mock_calls[-1][1][1]

    assert msg.meta.msg_type == "create"
    assert msg.data["field1"] == 2


@patch_producer()
def test_squash_create_delete(producer_m):
    producer_send_m = producer_m.return_value.send
    assert len(producer_send_m.mock_calls) == 0

    with squash():
        obj = ModelA.objects.create(field1=1, field2=2)
        obj.delete()

    assert len(producer_send_m.mock_calls) == 0
