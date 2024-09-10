from collections.abc import Generator, Iterable
from contextlib import contextmanager
from typing import TypeAlias

from django.db.models import Model

from .constants import TYPE_CREATE, TYPE_DELETE, TYPE_UPDATE
from .context import _context
from .stream import Streamer
from .types import Message, ObjectID

SquashItem: TypeAlias = dict[ObjectID, Message]
SquashDict: TypeAlias = dict[type[Model], SquashItem]

_context.squash = None


def is_squashing() -> bool:
    return getattr(_context, "squash", None) is not None


@contextmanager
def squash() -> Generator[None, None]:
    """
    Context manager to squash messages. Within this context manager messages is
    not sends immediately but accumulates in the buffer. Items in buffer is
    grouped by object ID, so that later items overrides earliest
    """
    from .registry import get_streamer

    is_top = not is_squashing()

    if is_top:
        squash: SquashDict = {}
        _context.squash = squash

    try:
        yield

    finally:
        if is_top:
            for model, messages_d in _context.squash.items():
                streamer = get_streamer(model)
                if streamer is not None:
                    messages = messages_d.values()
                    streamer.send_messages(messages)

            _context.squash = None


def add_to_squash(
    model: type[Model],
    streamer: Streamer,
    messages: Iterable[Message],
) -> int:
    assert _context.squash is not None
    squash: SquashDict = _context.squash

    squash.setdefault(model, {})
    messages_d = squash[model]
    count = 0

    for msg in messages:
        obj_id = msg.data[streamer.id_field]

        if obj_id in messages_d:
            prev_type = messages_d[obj_id].meta.msg_type
            cur_type = msg.meta.msg_type
            if prev_type == TYPE_CREATE and cur_type == TYPE_UPDATE:
                msg = msg._replace(
                    meta=msg.meta._replace(msg_type=TYPE_CREATE),
                )
            elif prev_type == TYPE_CREATE and cur_type == TYPE_DELETE:
                del messages_d[obj_id]
                continue

        messages_d[obj_id] = msg
        count += 1

    return count
