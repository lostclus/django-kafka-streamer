from contextlib import contextmanager
from threading import local

from .constants import TYPE_CREATE, TYPE_DELETE, TYPE_UPDATE
from .registry import get_streamer

_context = local()
_context.squash = None


@contextmanager
def set_context(user=None, source=None):
    """
    Context manager to setting message streamer context variables
    """
    _context.user = user
    _context.source = source
    yield
    _context.user = None
    _context.source = None


@contextmanager
def stop_handlers(*models):
    """
    Context manager to stop handlers for particular or all models
    """
    _context.stop_handlers = set(models)
    yield
    _context.stop_handlers = None


@contextmanager
def squash():
    """
    Context manager to squash messages. Within this context manager messages is
    not sends immediately but accumulates in the buffer. Items in buffer is
    grouped by object ID, so that later items overrides earliest
    """
    is_top = getattr(_context, "squash", None) is None

    if is_top:
        _context.squash = {}

    try:
        yield

    finally:
        if is_top:
            for model, messages_d in _context.squash.items():
                streamer = get_streamer(model)
                messages = messages_d.values()
                streamer.send_messages(messages)

            _context.squash = None


def _add_to_squash(squash, model, streamer, messages):
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
