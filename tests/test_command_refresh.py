from unittest import mock

from django.core.management import call_command

from tests.testapp.models import ModelA, ModelB


@mock.patch("kafkastreamer.management.commands.kafkastreamer_refresh.refresh")
def test_refresh(refresh_m):
    call_command("kafkastreamer_refresh")
    refresh_m.mock_calls == [
        mock.call(models=None, source=None),
    ]


@mock.patch("kafkastreamer.management.commands.kafkastreamer_refresh.refresh")
def test_refresh_with_models_and_source(refresh_m):
    call_command(
        "kafkastreamer_refresh",
        models=["ModelA"],
        source="custom-source",
    )
    refresh_m.mock_calls == [
        mock.call(models=["ModelA"], source="custom-source"),
    ]


@mock.patch("kafkastreamer.management.commands.kafkastreamer_refresh.full_refresh")
def test_refresh_no_async(full_refresh_m):
    call_command("kafkastreamer_refresh", no_async=True)
    full_refresh_m.mock_calls == [
        mock.call(),
    ]


@mock.patch("kafkastreamer.management.commands.kafkastreamer_refresh.full_refresh")
def test_refresh_no_async_with_models(full_refresh_m):
    call_command(
        "kafkastreamer_refresh",
        no_async=True,
        models=["testapp.ModelA", "testapp.ModelB"],
    )
    full_refresh_m.mock_calls == [
        mock.call(ModelA),
        mock.call(ModelB),
    ]
