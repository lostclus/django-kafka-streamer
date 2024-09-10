from collections import namedtuple
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeAlias

MessageContext = namedtuple(
    "MessageContext",
    [
        "source",  # source of data modification as string
        "user_id",  # author of data modification as user ID
        "extra",  # extra context data as dict
    ],
)

MessageMeta = namedtuple(
    "MessageMeta",
    [
        "timestamp",  # message time as datetime object
        "msg_type",  # message type as string
        "context",  # MessageContext
    ],
)

Message = namedtuple(
    "Message",
    [
        "meta",  # MessageMeta
        "obj_id",  # object ID (primary key)
        "data",  # message data as dict
    ],
)

ObjectID: TypeAlias = int | str

MessageSerializer: TypeAlias = Callable[..., bytes]
PartitionKeySerializer: TypeAlias = Callable[..., bytes]
Partitioner: TypeAlias = Callable[[bytes, list[int], list[int]], int]

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser

    User: TypeAlias = AbstractBaseUser | AnonymousUser
else:
    User: TypeAlias = Any
