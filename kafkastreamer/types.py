from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, NamedTuple, TypeAlias

ObjectID: TypeAlias = int | str
"Type alias for object ID."


class MessageContext(NamedTuple):
    "Message context."

    source: str
    "Source of data modification as string."

    user_id: ObjectID
    "Author of data modification as user ID."

    extra: dict[str, Any] | None
    "Extra context data as dict."


class MessageMeta(NamedTuple):
    "Message meta data."

    timestamp: datetime
    "Message time as datetime object."

    msg_type: str
    "Message type as string."

    context: MessageContext
    "Message context."


class Message(NamedTuple):
    "Represents message."

    meta: MessageMeta
    "Meta data."

    obj_id: ObjectID | None
    "Object ID (primary key)."

    data: dict[str, Any]
    "Message data as dict."


MessageSerializer: TypeAlias = Callable[..., bytes]
"Type alias for message serializer function."

PartitionKeySerializer: TypeAlias = Callable[..., bytes]
"Type alias for partition key serializer function."

Partitioner: TypeAlias = Callable[[bytes, list[int], list[int]], int]
"Type alias for partitioner function."


class RefreshFinalizeType(str, Enum):
    ENUMERATE = "enumerate"
    "Send enumerate IDs message."

    EOS = "eos"
    "Send end of stream message."


if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser

    User: TypeAlias = AbstractBaseUser | AnonymousUser
else:
    User: TypeAlias = Any
