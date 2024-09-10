import logging
import uuid
from collections.abc import Generator, Iterable, Sequence
from datetime import datetime
from typing import Any, cast

from django.core.exceptions import FieldError, ImproperlyConfigured, ObjectDoesNotExist
from django.db.models import FileField, Manager, Model
from django.db.models.query import QuerySet
from django.utils import timezone
from kafka import KafkaProducer  # type: ignore
from kafka.errors import KafkaTimeoutError, NoBrokersAvailable  # type: ignore

from .constants import TYPE_DELETE, TYPE_ENUMERATE, TYPE_EOS, TYPE_REFRESH
from .context import _context
from .settings import get_setting
from .types import (
    Message,
    MessageContext,
    MessageMeta,
    MessageSerializer,
    ObjectID,
    Partitioner,
    PartitionKeySerializer,
)

log = logging.getLogger(__name__)


class Batch:
    """
    Represents batch operation
    """

    def __init__(
        self,
        objects: Iterable[Model] | None = None,
        queryset: QuerySet | None = None,
        manager: Manager | None = None,
        objects_ids: Sequence[ObjectID] | None = None,
        select_related: Sequence[str] | None = None,
        prefetch_related: Sequence[str] | None = None,
        **kwargs: Any,
    ):
        self.objects = objects
        self.queryset = queryset
        self.manager = manager
        self.objects_ids = objects_ids
        self.select_related = select_related
        self.prefetch_related = prefetch_related

        assert (
            self.manager is not None
            or self.queryset is not None
            or self.objects is not None
        )

        self.model: type[Model] | None = None
        if self.manager is not None:
            self.model = self.manager.model
        elif self.queryset is not None:
            self.model = self.queryset.model

    def get_objects(self) -> QuerySet | Iterable[Model]:
        queryset = self.queryset
        if queryset is None and self.manager is not None:
            queryset = self.manager.all()

        if queryset is not None and self.objects_ids is not None:
            queryset = queryset.filter(pk__in=self.objects_ids).order_by()
            if self.select_related:
                queryset = queryset.select_related(*self.select_related)
            if self.prefetch_related:
                queryset = queryset.prefetch_related(*self.prefetch_related)
            return queryset

        if self.objects is not None:
            return self.objects

        raise Exception("Invalid batch")


class Streamer:
    """
    This class encapsulates all streaming logic for particular Django model
    class
    """

    topic: str | None = None  # Kafka topic for this class of objects
    exclude: Sequence[str] | None = None  # data fields to exclude

    # list of extra (related, computed) fields to include
    include: Sequence[str] | None = None

    # list of related fields to select in queryset
    select_related: Sequence[str] | None = None

    # list of related fields to prefetch in queryset
    prefetch_related: Sequence[str] | None = None

    # list of related fields to handle changes
    handle_related: Sequence[str] | None = None

    batch_class: type[Batch] = Batch
    refresh_finalize_type: str = "enumerate"
    batch_size: int | None = None
    message_serializer: MessageSerializer | None = None
    partition_key_serializer: PartitionKeySerializer | None = None
    partitioner: Partitioner | None = None
    id_field: str = "id"
    enumerate_ids_field: str = "ids"
    enumerate_chunk_field: str = "chunk"

    def __init__(self, **kwargs: Any):
        """
        Streamer constructor
        """
        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)
        if not self.topic:
            raise ImproperlyConfigured("No streamer topic specified")
        self.batch_size = self.batch_size or get_setting("BATCH_SIZE")
        if self.message_serializer is None:
            self.message_serializer = get_setting(
                "DEFAULT_MESSAGE_SERIALIZER", resolve=True
            )
        if self.partition_key_serializer is None:
            self.partition_key_serializer = get_setting(
                "DEFAULT_PARTITION_KEY_SERIALIZER", resolve=True
            )
        if self.partitioner is None:
            self.partitioner = get_setting("DEFAULT_PARTITIONER", resolve=True)

    def get_data_for_object(self, obj: Model, batch: Batch) -> dict[str, Any]:
        """
        Returns data fields for given object
        """

        def get_concrete_fields(
            obj: Model,
            batch: Batch,
            related_name: str | None = None,
            exclude: Sequence[str] | None = None,
        ) -> dict[str, Any]:
            if exclude and related_name:
                exclude = [
                    f[len(related_name) + 1 :]
                    for f in exclude
                    if f.startswith(related_name + ".")
                ]

            data = {}
            for f in obj._meta.concrete_fields:  # type: ignore
                if exclude and f.name in exclude:
                    continue
                if isinstance(f, FileField):
                    continue

                if related_name:
                    method_name = "load_%s__%s" % (related_name, f.attname)
                else:
                    method_name = "load_%s" % f.attname
                func = getattr(self, method_name, None)

                if func is not None:
                    value = func(obj, batch)
                else:
                    value = getattr(obj, f.attname)

                data[f.attname] = value

            return data

        data = get_concrete_fields(obj, batch, exclude=self.exclude)

        if self.include:
            for name in self.include:
                method_name = "load_%s" % name
                func = getattr(self, method_name, None)
                try:
                    if func is not None:
                        value = func(obj, batch)
                    else:
                        value = getattr(obj, name)
                except ObjectDoesNotExist:
                    value = None

                if isinstance(value, Manager):
                    value = value.all()
                if isinstance(value, (QuerySet, list, tuple)):
                    value_list = []
                    for sub_value in value:
                        if isinstance(sub_value, Model):
                            value_list.append(
                                get_concrete_fields(
                                    sub_value,
                                    batch,
                                    related_name=name,
                                    exclude=self.exclude,
                                )
                            )
                        else:
                            value_list.append(sub_value)
                    value = value_list
                elif isinstance(value, Model):
                    value = get_concrete_fields(
                        value, batch, related_name=name, exclude=self.exclude
                    )

                data[name] = value

        return data

    def get_id(self, obj: Model, batch: Batch) -> ObjectID | None:
        return obj.pk or getattr(obj, "_kafkastreamer_pre_delete_pk", None)

    def get_message(
        self,
        obj: Model,
        batch: Batch,
        msg_type: str | None = None,
        timestamp: datetime | None = None,
    ) -> Message:
        """
        Returns Message tuple for given obj and message type
        """
        if msg_type is None:
            msg_type = TYPE_REFRESH
        if timestamp is None:
            timestamp = timezone.now()

        meta = MessageMeta(
            timestamp=timestamp,
            msg_type=msg_type,
            context=self.get_context_info(),
        )
        data = self.get_data_for_object(obj, batch)
        extra = self.get_extra_data(obj, batch)
        if extra:
            data.update(extra)

        obj_id = self.get_id(obj, batch)
        msg = Message(meta=meta, obj_id=obj_id, data=data)
        return msg

    def get_delete_message(
        self,
        obj_id: ObjectID,
        timestamp: datetime,
        obj: Model | None = None,
        batch: Batch | None = None,
    ) -> Message:
        """
        Returns Message tuple for delete message type for given object ID
        """
        meta = MessageMeta(
            timestamp=timestamp,
            msg_type=TYPE_DELETE,
            context=self.get_context_info(),
        )
        data = {
            self.id_field: obj_id,
        }
        extra = self.get_extra_data(obj, batch)
        if extra:
            data.update(extra)

        msg = Message(meta=meta, obj_id=obj_id, data=data)
        return msg

    def get_enumerate_message(
        self,
        objects_ids: Sequence[ObjectID],
        timestamp: datetime,
        batch: Batch | None = None,
        chunk_index: int | None = None,
        chunk_total: int | None = None,
        chunk_session: str | None = None,
    ) -> Message:
        """
        Returns Message tuple for enumerate message type for given objects IDs
        """
        meta = MessageMeta(
            timestamp=timestamp,
            msg_type=TYPE_ENUMERATE,
            context=self.get_context_info(),
        )
        data: dict[str, Any] = {
            self.enumerate_ids_field: objects_ids,
        }
        if chunk_index is not None and chunk_total and chunk_session:
            data[self.enumerate_chunk_field] = {
                "index": chunk_index,
                "count": chunk_total,
                "session": chunk_session,
            }
        extra = self.get_extra_data(None, batch)
        if extra:
            data.update(extra)
        obj_id = objects_ids and objects_ids[0] or None

        msg = Message(meta=meta, obj_id=obj_id, data=data)
        return msg

    def get_eos_message(self, timestamp: datetime) -> Message:
        """
        Returns Message tuple for end of stream message type
        """
        meta = MessageMeta(
            timestamp=timestamp,
            msg_type=TYPE_EOS,
            context=self.get_context_info(),
        )
        msg = Message(meta=meta, obj_id=None, data={})
        return msg

    def get_context_info(self) -> MessageContext:
        """
        Returns context information fields
        """
        source = getattr(_context, "source", None) or get_setting("DEFAULT_SOURCE")
        user = getattr(_context, "user", None)
        if user is not None and user.is_authenticated():
            user_id = user.pk
        else:
            user_id = None
        context = MessageContext(
            source=source,
            user_id=user_id,
            extra=None,
        )
        return context

    def get_extra_data(
        self, obj: Model | None, batch: Batch | None
    ) -> dict[str, Any] | None:
        """
        Returns extra data fields for given object or batch
        """
        return None

    def get_batch(
        self,
        objects: Iterable[Model] | None = None,
        queryset: QuerySet | None = None,
        manager: Manager | None = None,
        objects_ids: Sequence[ObjectID] | None = None,
        **kwargs: Any,
    ) -> Batch:
        return self.batch_class(
            objects=objects,
            queryset=queryset,
            manager=manager,
            objects_ids=objects_ids,
            select_related=self.select_related,
            prefetch_related=self.prefetch_related,
            **kwargs,
        )

    def get_messages_for_batch(
        self,
        batch: Batch,
        msg_type: str | None = None,
        timestamp: datetime | None = None,
    ) -> Generator[Message, None]:
        """
        Returns Message tuples for batch of objects
        """
        try:
            for obj in batch.get_objects():
                yield self.get_message(
                    obj,
                    batch=batch,
                    msg_type=msg_type,
                    timestamp=timestamp,
                )
        except FieldError as e:
            log.error("FieldError for model: %s: %s", batch.model, e)
            raise

    def get_messages_for_objects(
        self,
        objects: Iterable[Model],
        manager: Manager | None = None,
        objects_ids: Sequence[ObjectID] | None = None,
        msg_type: str | None = None,
        timestamp: datetime | None = None,
        batch_size: int | None = None,
        batch_kwargs: dict[str, Any] | None = None,
    ) -> Generator[Message, None]:
        """
        Returns Message tuples for given objects with given message type
        """
        if timestamp is None:
            timestamp = timezone.now()
        batch_size = batch_size or self.batch_size

        queryset = None

        if isinstance(objects, Manager):
            manager = objects
            queryset = objects.all()
        elif isinstance(objects, QuerySet):
            queryset = objects

        if queryset is not None and batch_size:
            if objects_ids is None:
                ids = list(queryset.distinct().order_by().values_list("pk", flat=True))
            else:
                ids = list(objects_ids)
            ids_chunked = [
                ids[i : i + batch_size] for i in range(0, len(ids), batch_size)
            ]
            for ids in ids_chunked:
                batch = self.get_batch(
                    queryset=queryset,
                    manager=manager,
                    objects_ids=ids,
                    **(batch_kwargs or {}),
                )
                messages = self.get_messages_for_batch(
                    batch, msg_type=msg_type, timestamp=timestamp
                )
                for msg in messages:
                    yield msg
        else:
            batch = self.get_batch(objects=objects, manager=manager)
            messages = self.get_messages_for_batch(
                batch,
                msg_type=msg_type,
                timestamp=timestamp,
            )
            for msg in messages:
                yield msg

    def get_messages_for_ids_delete(
        self,
        objects_ids: Sequence[ObjectID],
        timestamp: datetime | None = None,
        manager: Manager | None = None,
    ) -> list[Message]:
        """
        Returns Message tuples for delete messages for given objects IDs
        """
        if timestamp is None:
            timestamp = timezone.now()

        batch = self.get_batch(objects_ids=objects_ids, manager=manager)
        messages = [
            self.get_delete_message(obj_id, timestamp, batch=batch)
            for obj_id in objects_ids
        ]
        return messages

    def get_producer_options(self) -> dict[str, Any]:
        return cast(dict[str, Any], get_setting("PRODUCER_OPTIONS"))

    def get_producer(self, **kwargs: Any) -> KafkaProducer | None:
        """
        Returns Kafka producer
        """
        options = {
            "value_serializer": self.message_serializer,
            "key_serializer": self.partition_key_serializer,
            "bootstrap_servers": get_setting("BOOTSTRAP_SERVERS"),
            **(
                {
                    "partitioner": self.partitioner,
                }
                if self.partitioner is not None
                else {}
            ),
            **self.get_producer_options(),
            **kwargs,
        }

        if options.get("bootstrap_servers") is None:
            raise ImproperlyConfigured(
                "The `KAFKA_STREAMER['BOOTSTRAP_SERVERS']` is not configured."
            )
        if options["bootstrap_servers"] == []:
            return None

        try:
            producer = KafkaProducer(**options)
        except NoBrokersAvailable as e:
            log.error("Kafka connect error: %s", e)
            return None

        return producer

    def send_messages(
        self,
        messages: Iterable[Message],
        batch_size: int | None = None,
        producer: KafkaProducer | None = None,
        flush: bool = True,
    ) -> int:
        """
        Sends given messages to Kafka
        """
        batch_size = batch_size or self.batch_size
        if producer is None:
            producer = self.get_producer()
        if producer is None:
            return 0

        messages_send_count = 0
        try:
            for msg in messages:
                if self.partition_key_serializer is not None:
                    key = msg
                else:
                    key = None
                producer.send(self.topic, msg, key=key)
                messages_send_count += 1
                if batch_size and messages_send_count % batch_size == 0:
                    producer.flush()

            if flush:
                producer.flush()
        except KafkaTimeoutError as e:
            log.error("Kafka connect error: %s", e)

        return messages_send_count

    def send_objects(
        self,
        objects: Iterable[Model],
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
        Sends given objects to Kafka
        """
        messages = self.get_messages_for_objects(
            objects,
            manager=manager,
            objects_ids=objects_ids,
            msg_type=msg_type,
            timestamp=timestamp,
            batch_size=batch_size,
            batch_kwargs=batch_kwargs,
        )
        return self.send_messages(
            messages,
            batch_size=batch_size,
            producer=producer,
            flush=flush,
        )

    def send_ids_delete(
        self,
        objects_ids: Sequence[ObjectID],
        timestamp: datetime | None = None,
        manager: Manager | None = None,
        batch_size: int | None = None,
        producer: KafkaProducer | None = None,
        flush: bool = True,
    ) -> int:
        """
        Sends delete messages for given objects IDs
        """
        messages = self.get_messages_for_ids_delete(
            objects_ids,
            timestamp=timestamp,
            manager=manager,
        )
        return self.send_messages(
            messages,
            batch_size=batch_size,
            producer=producer,
            flush=flush,
        )

    def send_ids_enumerate(
        self,
        objects_ids: Sequence[ObjectID],
        timestamp: datetime | None = None,
        manager: Manager | None = None,
        producer: KafkaProducer | None = None,
        flush: bool = True,
        chunk_size: int = 5000,
    ) -> int:
        """
        Sends enumerate message for given objects IDs
        """
        if timestamp is None:
            timestamp = timezone.now()

        batch = self.get_batch(manager=manager)
        if len(objects_ids) <= chunk_size:
            messages = [
                self.get_enumerate_message(
                    objects_ids,
                    timestamp,
                    batch=batch,
                ),
            ]
        else:
            ids_chunked = [
                objects_ids[i : i + chunk_size]
                for i in range(0, len(objects_ids), chunk_size)
            ]
            chunk_session = str(uuid.uuid4())
            messages = [
                self.get_enumerate_message(
                    ids,
                    timestamp,
                    batch=batch,
                    chunk_index=idx,
                    chunk_total=len(ids_chunked),
                    chunk_session=chunk_session,
                )
                for idx, ids in enumerate(ids_chunked)
            ]

        return self.send_messages(messages, producer=producer, flush=flush)

    def send_eos(
        self,
        timestamp: datetime | None = None,
        producer: KafkaProducer | None = None,
        flush: bool = True,
    ) -> int:
        """
        Sends end of stream messages
        """
        if timestamp is None:
            timestamp = timezone.now()
        msg = self.get_eos_message(timestamp=timestamp)
        return self.send_messages([msg], producer=producer, flush=flush)
