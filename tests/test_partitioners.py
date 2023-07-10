from unittest import mock

import pytest

from kafkastreamer.partitioners import modulo_partitioner


@pytest.mark.parametrize(
    ("key", "all_partitions", "available", "expected"),
    (
        (b"1", range(8), None, 1),
        (b"2", range(8), None, 2),
        (b"7", range(8), None, 7),
        (b"8", range(8), None, 0),
        (b"", range(8), None, 3),
        (b"1", None, [1, 0], 1),
        (b"2", None, [1, 0], 0),
    ),
)
@mock.patch("random.choice", lambda x: 3)
def test_modulo_partitioner(key, all_partitions, available, expected):
    part = modulo_partitioner(key, all_partitions, available)
    assert part == expected
