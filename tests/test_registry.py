from unittest import mock

import pytest

from kafkastreamer.registry import (
    RegistryKey,
    _registry,
    autodiscover,
    get_registry,
    get_streamer,
    get_streamer_for_related,
    register,
)
from tests.testapp.models import ModelA, ModelC
from tests.testapp.streamers import ModelAStreamer


@pytest.fixture()
def registry():
    old_registry = _registry.copy()
    try:
        _registry.clear()
        yield _registry
    finally:
        _registry.clear()
        _registry.update(old_registry)


@mock.patch("kafkastreamer.registry.import_module")
def test_autodiscover(import_module_m):
    autodiscover()
    import_module_m.assert_called_with("kafkastreamer.streamers")


def test_get_streamer(registry):
    key = RegistryKey("testapp", "ModelA", None)
    registry[key] = ModelAStreamer()
    streamer = get_streamer(ModelA)
    assert streamer is registry[key]


def test_get_streamer_for_related(registry):
    streamer = ModelAStreamer()
    key1 = RegistryKey("testapp", "ModelA", "some_relation_1")
    key2 = RegistryKey("testapp", "ModelA", "some_relation_2")
    registry[key1] = streamer
    registry[key2] = streamer
    result = sorted(get_streamer_for_related(ModelA))
    assert result == [
        ("some_relation_1", streamer),
        ("some_relation_2", streamer),
    ]


def test_get_registry(registry):
    register(ModelA, ModelAStreamer)
    streamer = get_streamer(ModelA)
    assert get_registry() == [
        (ModelA, streamer),
    ]


def test_register(registry):
    assert registry == {}
    register(ModelA, ModelAStreamer)
    key = RegistryKey("testapp", "ModelA", None)
    assert key in registry
    assert isinstance(registry[key], ModelAStreamer)


def test_register_with_related(registry):
    class ModelCStreamerHandleRelated(ModelAStreamer):
        handle_related = ["a", "b"]

    assert registry == {}
    register(ModelC, ModelCStreamerHandleRelated)

    key = RegistryKey("testapp", "ModelC", None)
    assert key in registry
    assert isinstance(registry[key], ModelCStreamerHandleRelated)

    key = RegistryKey("testapp", "ModelA", "modelc_set")
    assert key in registry
    assert isinstance(registry[key], ModelCStreamerHandleRelated)

    key = RegistryKey("testapp", "ModelB", "modelc_set")
    assert key in registry
    assert isinstance(registry[key], ModelCStreamerHandleRelated)
