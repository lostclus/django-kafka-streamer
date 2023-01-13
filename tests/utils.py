import datetime
import functools
from unittest import mock

patch_now = functools.partial(
    mock.patch,
    "django.utils.timezone.now",
    new=lambda: datetime.datetime(2023, 1, 1, 0, 0, 0),
)

patch_producer = functools.partial(
    mock.patch,
    "kafkastreamer.stream.Streamer.get_producer",
)
