import logging
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Manager, Model
from django.utils import timezone

from .constants import TYPE_CREATE, TYPE_DELETE, TYPE_UPDATE
from .context import is_model_handler_stopped
from .registry import get_streamer, get_streamer_for_related
from .squashing import add_to_squash, is_squashing

log = logging.getLogger(__name__)


def handle_post_save(
    sender: type[Model], instance: Model | None = None, **kwargs: Any
) -> None:
    if instance is None:
        return
    if is_model_handler_stopped(sender):
        log.debug(f"The post_save handler for {sender.__name__} is stopped")
        return

    log.debug(f"Entering post_save handler for {sender.__name__}")

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
        log.debug(
            f"Processing related field {rel_name} in post_save handler for"
            f" {sender.__name__}"
        )
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
            count = add_to_squash(model, streamer, messages)
        else:
            count = streamer.send_messages(messages)
        log.debug(
            f"Send {count} messages for related field {rel_name} in "
            f"post_save handler for {sender.__name__}"
        )


def handle_pre_delete(sender: type[Model], instance: Model, **kwargs: Any) -> None:
    log.debug(f"Entering pre_delete handler for {sender.__name__}")
    setattr(instance, "_kafkastreamer_pre_delete_pk", instance.pk)

    for rel_name, streamer in get_streamer_for_related(sender):
        log.debug(
            f"Processing related field {rel_name} in pre_delete handler for"
            f" {sender.__name__}"
        )
        try:
            rel = getattr(instance, rel_name)
        except ObjectDoesNotExist:
            continue
        if isinstance(rel, Manager):
            objects = list(rel.all())
            setattr(instance, f"_kafkastreamer_pre_delete_{rel_name}_cache", objects)


def handle_post_delete(
    sender: type[Model], instance: Model | None = None, **kwargs: Any
) -> None:
    if instance is None:
        return
    if is_model_handler_stopped(sender):
        log.debug(f"The post_delete handler for {sender.__name__} is stopped")
        return

    log.debug(f"Entering post_delete handler for {sender.__name__}")

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
        log.debug(
            f"Processing related field {rel_name} in post_delete handler for"
            f" {sender.__name__}"
        )
        try:
            rel = getattr(instance, rel_name)
        except ObjectDoesNotExist:
            continue

        if isinstance(rel, Model):
            # The deleted object may be cached in this instance so that call
            # refresh_from_db here
            rel.refresh_from_db()
            messages = streamer.get_messages_for_objects(
                [rel],
                msg_type=TYPE_UPDATE,
                timestamp=timestamp,
            )
            model = rel.__class__
        elif isinstance(rel, Manager):
            objects = getattr(
                instance, f"_kafkastreamer_pre_delete_{rel_name}_cache", rel.all()
            )
            messages = streamer.get_messages_for_objects(
                objects,
                msg_type=TYPE_UPDATE,
                timestamp=timestamp,
            )
            model = rel.model
        else:
            continue
        if is_squashing():
            count = add_to_squash(model, streamer, messages)
        else:
            count = streamer.send_messages(messages)
        log.debug(
            f"Send {count} messages for related field {rel_name} in "
            f"post_delete handler for {sender.__name__}"
        )


def handle_m2m_changed(
    sender: type[Model],
    instance: Model | None = None,
    action: str | None = None,
    **kwargs: Any,
) -> None:
    if instance is None:
        return
    log.debug(
        f"Entering m2m_changed handler for {sender.__name__} with action {action}"
    )
    if action and action.startswith("post_"):
        handle_post_save(instance.__class__, instance=instance, **kwargs)
