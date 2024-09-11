from kafkastreamer import squash
from tests.testapp.models import ModelA
from tests.utils import patch_producer


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
