import json

from django.core.serializers.json import DjangoJSONEncoder

DEFAULT_ENCODING = "utf-8"


def flat_json_message_serializer(
    msg,
    cls=DjangoJSONEncoder,
    ensure_id=True,
    ensure_ascii=False,
    encoding=DEFAULT_ENCODING,
):
    meta = msg.meta
    context = meta.context

    context_fields = {}
    if context.source:
        context_fields["_source"] = context.source
    if context.user_id:
        context_fields["_user_id"] = context.user_id
    if context.extra:
        for field, value in context.extra.items():
            context_fields[f"_{field}"] = value

    item = {
        "_time": meta.timestamp,
        "_type": meta.msg_type,
        **context_fields,
        **msg.data,
    }
    if ensure_id and item.get("id") is None:
        item["id"] = msg.obj_id

    return json.dumps(
        item,
        cls=cls,
        ensure_ascii=ensure_ascii,
    ).encode(
        encoding,
    )


def object_id_key_serializer(msg, encoding=DEFAULT_ENCODING):
    """
    Returns key based on object ID as encoded string of digits.
    """
    return bytes(str(msg.obj_id or 0), encoding)
