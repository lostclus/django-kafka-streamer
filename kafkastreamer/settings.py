from django.conf import settings

DEFAULTS = {
    "BOOTSTRAP_SERVERS": None,
    "PRODUCER_OPTIONS": {},
    "BATCH_SIZE": 500,
    "DEFAULT_SOURCE": None,
}


def get_setting(setting_name):
    value = settings.KAFKA_STREAMER.get(
        setting_name,
        DEFAULTS[setting_name],
    )
    return value
