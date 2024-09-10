from typing import Any

from django.conf import settings
from django.utils.module_loading import import_string

DEFAULTS: dict[str, Any] = {
    "BOOTSTRAP_SERVERS": None,
    "PRODUCER_OPTIONS": {},
    "BATCH_SIZE": 500,
    "DEFAULT_SOURCE": None,
    "DEFAULT_MESSAGE_SERIALIZER": (
        "kafkastreamer.serializers.flat_json_message_serializer"
    ),
    "DEFAULT_PARTITION_KEY_SERIALIZER": None,
    "DEFAULT_PARTITIONER": None,
}


def get_setting(setting_name: str, resolve: bool = False) -> Any:
    value = settings.KAFKA_STREAMER.get(
        setting_name,
        DEFAULTS[setting_name],
    )
    if resolve and type(value) is str:
        value = import_string(value)
    return value
