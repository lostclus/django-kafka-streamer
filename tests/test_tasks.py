from unittest import mock

from kafkastreamer.tasks import refresh, refresh_model
from tests.testapp.models import ModelA


@mock.patch("kafkastreamer.tasks.refresh_model")
def test_refresh(refresh_model_m):
    result = refresh()

    assert result == {"models_count": 7}

    refresh_model_m.delay.assert_has_calls(
        [
            mock.call(model_name="testapp.ModelA", source=None),
            mock.call(model_name="testapp.ModelB", source=None),
            mock.call(model_name="testapp.ModelC", source=None),
            mock.call(model_name="testapp.ModelD", source=None),
            mock.call(model_name="testapp.ModelE", source=None),
            mock.call(model_name="testapp.ModelF", source=None),
            mock.call(model_name="testapp.ModelG", source=None),
        ],
        any_order=True,
    )


@mock.patch("kafkastreamer.tasks.refresh_model")
def test_refresh_with_models_and_source(refresh_model_m):
    result = refresh(models=["testapp.ModelA"], source="custom-source")

    assert result == {"models_count": 1}

    refresh_model_m.delay.assert_has_calls(
        [
            mock.call(model_name="testapp.ModelA", source="custom-source"),
        ],
        any_order=True,
    )


@mock.patch("kafkastreamer.full_refresh")
def test_refresh_model(full_refresh_m):
    full_refresh_m.return_value = 12345
    result = refresh_model("testapp.ModelA")
    assert result == {"messages_count": 12345}
    assert full_refresh_m.mock_calls == [
        mock.call(ModelA),
    ]
