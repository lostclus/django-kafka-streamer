import random


def modulo_partitioner(
    key: bytes, all_partitions: list[int], available: list[int]
) -> int:
    """
    Returns partition by formula int(key) % len(partiotons). Assume that key is
    bytes containing ASCII digits. If key is empty then random partition will
    be returned.
    """
    parts = sorted(available) if available else all_partitions

    if key == b"":
        return random.choice(parts)

    n = int(key.decode("ascii"))
    p = parts[n % len(parts)]
    return p
