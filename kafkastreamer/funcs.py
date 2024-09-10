from collections.abc import Sequence
from datetime import datetime
from typing import Any

from django.db.models import Manager, Model
from django.db.models.query import QuerySet
from django.utils import timezone
from kafka import KafkaProducer  # type: ignore

from .constants import TYPE_CREATE, TYPE_DELETE, TYPE_REFRESH, TYPE_UPDATE
from .registry import get_registry, get_streamer
from .squashing import add_to_squash, is_squashing
from .stream import Streamer
from .types import ObjectID


def send(
    objects: Sequence[Model],
    manager: Manager | None = None,
    objects_ids: Sequence[ObjectID] | None = None,
    msg_type: str | None = None,
    timestamp: datetime | None = None,
    batch_size: int | None = None,
    batch_kwargs: dict[str, Any] | None = None,
    producer: KafkaProducer | None = None,
    flush: bool = True,
) -> int:
    """
    Sends objects to associated streamer
    """
    if manager is not None:
        model = manager.model
    elif isinstance(objects, (Manager, QuerySet)):
        model = objects.model
    else:
        if not objects:
            return 0
        model = objects[0].__class__

    streamer = get_streamer(model)
    if streamer is None:
        return 0

    messages = streamer.get_messages_for_objects(
        objects,
        manager=manager,
        objects_ids=objects_ids,
        msg_type=msg_type,
        timestamp=timestamp,
        batch_size=batch_size,
        batch_kwargs=batch_kwargs,
    )

    if is_squashing():
        count = add_to_squash(model, streamer, messages)
    else:
        count = streamer.send_messages(
            messages,
            batch_size=batch_size,
            producer=producer,
            flush=flush,
        )

    return count


def send_create(objects: Sequence[Model], **kwargs: Any) -> int:
    return send(objects, msg_type=TYPE_CREATE, **kwargs)


def send_update(objects: Sequence[Model], **kwargs: Any) -> int:
    return send(objects, msg_type=TYPE_UPDATE, **kwargs)


def send_delete(objects: Sequence[Model], **kwargs: Any) -> int:
    return send(objects, msg_type=TYPE_DELETE, **kwargs)


def send_refresh(objects: Sequence[Model], **kwargs: Any) -> int:
    return send(objects, msg_type=TYPE_REFRESH, **kwargs)


def full_refresh(
    model_or_manager: type[Model] | Manager | None = None,
    producer: KafkaProducer | None = None,
    flush: bool = True,
) -> int:
    """
    Does full refresh for model or manager. Sends refresh message for each
    object, then sends enumerate message with objects IDs
    """

    def _refresh(
        streamer: Streamer,
        manager: Manager,
        producer: KafkaProducer,
        flush: bool,
        timestamp: datetime | None = None,
    ) -> int:
        if timestamp is None:
            timestamp = timezone.now()

        queryset = manager.all()
        objects_ids = list(queryset.order_by().values_list("pk", flat=True))

        count = streamer.send_objects(
            queryset,
            manager=manager,
            objects_ids=objects_ids,
            msg_type=TYPE_REFRESH,
            timestamp=timestamp,
            producer=producer,
            flush=False,
        )
        if streamer.refresh_finalize_type == "enumerate":
            count += streamer.send_ids_enumerate(
                objects_ids,
                manager=manager,
                timestamp=timestamp,
                producer=producer,
                flush=flush,
            )
        elif streamer.refresh_finalize_type == "eos":
            count += streamer.send_eos(
                timestamp=timestamp, producer=producer, flush=flush
            )

        return count

    streamer_manager_list: list[tuple[Streamer, Manager]] = []

    if model_or_manager is None:
        streamer_manager_list.extend(
            [(streamer, model._default_manager) for model, streamer in get_registry()]
        )
    elif isinstance(model_or_manager, Manager):
        manager = model_or_manager
        model = manager.model
        streamer = get_streamer(model)
        if streamer is not None:
            streamer_manager_list.append((streamer, manager))
    else:
        model = model_or_manager
        manager = model._default_manager
        streamer = get_streamer(model)
        if streamer is not None:
            streamer_manager_list.append((streamer, manager))

    count = 0
    for streamer, manager in streamer_manager_list:
        if producer is None:
            producer = streamer.get_producer()
        count += _refresh(streamer, manager, producer, flush)

    return count
