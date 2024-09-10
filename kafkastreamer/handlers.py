from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Manager, Model
from django.utils import timezone

from .constants import TYPE_CREATE, TYPE_DELETE, TYPE_UPDATE
from .context import is_model_handler_stopped
from .registry import get_streamer, get_streamer_for_related
from .squashing import add_to_squash, is_squashing


def handle_post_save(
    sender: type[Model], instance: Model | None = None, **kwargs: Any
) -> None:
    if instance is None:
        return
    if is_model_handler_stopped(sender):
        return

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
        if is_squashing():
            add_to_squash(sender, streamer, messages)
        else:
            streamer.send_messages(messages)

    for rel_name, streamer in get_streamer_for_related(sender):
        try:
            rel = getattr(instance, rel_name)
        except ObjectDoesNotExist:
            continue

        if isinstance(rel, Model):
            setattr(rel, "_kafkastreamer_from_related", instance)
            messages = streamer.get_messages_for_objects(
                [rel],
                msg_type=TYPE_UPDATE,
                timestamp=timestamp,
            )
            model = rel.__class__
        elif isinstance(rel, Manager):
            messages = streamer.get_messages_for_objects(
                rel.all(),
                msg_type=TYPE_UPDATE,
                timestamp=timestamp,
            )
            model = rel.model
        else:
            continue
        if is_squashing():
            add_to_squash(model, streamer, messages)
        else:
            streamer.send_messages(messages)


def handle_pre_delete(sender: type[Model], instance: Model, **kwargs: Any) -> None:
    setattr(instance, "_kafkastreamer_pre_delete_pk", instance.pk)


def handle_post_delete(
    sender: type[Model], instance: Model | None = None, **kwargs: Any
) -> None:
    if instance is None:
        return
    if is_model_handler_stopped(sender):
        return

    msg_type = TYPE_DELETE
    timestamp = timezone.now()

    streamer = get_streamer(sender)
    if streamer is not None:
        messages = streamer.get_messages_for_objects(
            [instance],
            msg_type=msg_type,
            timestamp=timestamp,
        )
        if is_squashing():
            add_to_squash(sender, streamer, messages)
        else:
            streamer.send_messages(messages)

    for rel_name, streamer in get_streamer_for_related(sender):
        try:
            rel = getattr(instance, rel_name)
        except ObjectDoesNotExist:
            continue

        if isinstance(rel, Model):
            messages = streamer.get_messages_for_objects(
                [rel],
                msg_type=TYPE_UPDATE,
                timestamp=timestamp,
            )
            model = rel.__class__
        elif isinstance(rel, Manager):
            messages = streamer.get_messages_for_objects(
                rel.all(),
                msg_type=TYPE_UPDATE,
                timestamp=timestamp,
            )
            model = rel.model
        else:
            continue
        if is_squashing():
            add_to_squash(model, streamer, messages)
        else:
            streamer.send_messages(messages)


def handle_m2m_changed(
    sender: type[Model],
    instance: Model | None = None,
    action: str | None = None,
    **kwargs: Any,
) -> None:
    if instance is None:
        return
    if action and action.startswith("post_"):
        handle_post_save(instance.__class__, instance=instance, **kwargs)
