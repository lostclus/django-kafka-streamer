from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone

from .constants import TYPE_CREATE, TYPE_DELETE, TYPE_UPDATE
from .context import _add_to_squash, _context
from .registry import get_streamer, get_streamer_for_related


def handle_post_save(sender, instance=None, **kwargs):
    stop_handlers = getattr(_context, "stop_handlers", None)
    if stop_handlers is not None:
        if not stop_handlers or sender in stop_handlers:
            return

    squash = getattr(_context, "squash", None)
    created = kwargs.get("created", False)
    msg_type = created and TYPE_CREATE or TYPE_UPDATE
    timestamp = timezone.now()

    streamer = get_streamer(sender)
    if streamer is not None:
        messages = streamer.get_messages_for_objects(
            [instance],
            msg_type=msg_type,
            timestamp=timestamp,
        )
        if squash is not None:
            _add_to_squash(squash, sender, streamer, messages)
        else:
            streamer.send_messages(messages)

    for rel_name, streamer in get_streamer_for_related(sender):
        try:
            rel = getattr(instance, rel_name)
        except ObjectDoesNotExist:
            continue

        messages = None
        if isinstance(rel, models.Model):
            rel._kafkastreamer_from_related = instance
            messages = streamer.get_messages_for_objects(
                [rel],
                msg_type=TYPE_UPDATE,
                timestamp=timestamp,
            )
            model = rel.__class__
        elif isinstance(rel, models.Manager):
            messages = streamer.get_messages_for_objects(
                rel,
                msg_type=TYPE_UPDATE,
                timestamp=timestamp,
            )
            model = rel.model
        if messages is not None:
            if squash is not None:
                _add_to_squash(squash, model, streamer, messages)
            else:
                streamer.send_messages(messages)


def handle_pre_delete(sender, instance, **kwargs):
    instance._kafkastreamer_pre_delete_pk = instance.pk


def handle_post_delete(sender, instance=None, **kwargs):
    stop_handlers = getattr(_context, "stop_handlers", None)
    if stop_handlers is not None:
        if not stop_handlers or sender in stop_handlers:
            return

    squash = getattr(_context, "squash", None)
    msg_type = TYPE_DELETE
    timestamp = timezone.now()

    streamer = get_streamer(sender)
    if streamer is not None:
        messages = streamer.get_messages_for_objects(
            [instance],
            msg_type=msg_type,
            timestamp=timestamp,
        )
        if squash is not None:
            _add_to_squash(squash, sender, streamer, messages)
        else:
            streamer.send_messages(messages)

    for rel_name, streamer in get_streamer_for_related(sender):
        try:
            rel = getattr(instance, rel_name)
        except ObjectDoesNotExist:
            continue

        messages = None
        if isinstance(rel, models.Model):
            messages = streamer.get_messages_for_objects(
                [rel],
                msg_type=TYPE_UPDATE,
                timestamp=timestamp,
            )
            model = rel.__class__
        elif isinstance(rel, models.Manager):
            messages = streamer.get_messages_for_objects(
                rel,
                msg_type=TYPE_UPDATE,
                timestamp=timestamp,
            )
            model = rel.model
        if messages is not None:
            if squash is not None:
                _add_to_squash(squash, model, streamer, messages)
            else:
                streamer.send_messages(messages)


def handle_m2m_changed(sender, instance=None, action=None, **kwargs):
    if action.startswith("post_"):
        handle_post_save(instance.__class__, instance=instance, **kwargs)
