from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, NamedTuple, TypeAlias

ObjectID: TypeAlias = int | str


class MessageContext(NamedTuple):
    source: str  # source of data modification as string
    user_id: ObjectID  # author of data modification as user ID
    extra: dict[str, Any] | None  # extra context data as dict


class MessageMeta(NamedTuple):
    timestamp: datetime  # message time as datetime object
    msg_type: str  # message type as string
    context: MessageContext  # MessageContext


class Message(NamedTuple):
    meta: MessageMeta  # MessageMeta
    obj_id: ObjectID | None  # object ID (primary key)
    data: dict[str, Any]  # message data as dict


MessageSerializer: TypeAlias = Callable[..., bytes]
PartitionKeySerializer: TypeAlias = Callable[..., bytes]
Partitioner: TypeAlias = Callable[[bytes, list[int], list[int]], int]


class RefreshFinalizeType(str, Enum):
    ENUMERATE = "enumerate"  # Send enumerate IDs message
    EOS = "eos"  # Send end of stream message


if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser

    User: TypeAlias = AbstractBaseUser | AnonymousUser
else:
    User: TypeAlias = Any
