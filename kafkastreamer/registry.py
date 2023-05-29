import collections
from importlib import import_module

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ForwardOneToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete

_registry = {}
RegistryKey = collections.namedtuple(
    "RegistryKey", ["app_label", "object_name", "rel_name"]
)


def _make_registry_key(model, rel_name=None):
    return RegistryKey(
        model._meta.app_label,
        model._meta.object_name,
        rel_name,
    )


def register(model, streamer_class=None, set_handlers=True, **kwargs):
    """
    Registers Django model using given streamer class. May be used as plain
    function call or as decorator on streamer class.
    """
    from .handlers import (
        handle_m2m_changed,
        handle_post_delete,
        handle_post_save,
        handle_pre_delete,
    )

    def wrapper(cls):
        register(model, cls)
        return cls

    if streamer_class is None:
        # Called as class decorator
        return wrapper

    streamer = streamer_class(**kwargs)
    _registry[_make_registry_key(model)] = streamer

    if set_handlers:
        post_save.connect(handle_post_save, sender=model)
        pre_delete.connect(handle_pre_delete, sender=model)
        post_delete.connect(handle_post_delete, sender=model)

    for rel_name in streamer.handle_related or []:
        rel_desc = getattr(model, rel_name)

        rel_model_and_attr = []

        if isinstance(rel_desc, ManyToManyDescriptor):
            rel_model_and_attr.append(
                (rel_desc.rel.model, rel_desc.rel.related_name, True)
            )
            rel_model_and_attr.append((rel_desc.rel.through, None, True))
        elif isinstance(rel_desc, ReverseManyToOneDescriptor):
            rel_model_and_attr.append(
                (rel_desc.rel.related_model, rel_desc.rel.field.name, True)
            )
        elif isinstance(
            rel_desc,
            (ForwardOneToOneDescriptor, ForwardManyToOneDescriptor),
        ):
            set_delete_handler = rel_desc.field.remote_field.on_delete != models.CASCADE
            rel_model_and_attr.append(
                (
                    rel_desc.field.related_model,
                    rel_desc.field.remote_field.name,
                    set_delete_handler,
                )
            )
        elif isinstance(rel_desc, ReverseOneToOneDescriptor):
            rel_model_and_attr.append(
                (rel_desc.related.related_model, rel_desc.related.field.name, True)
            )

        for rel_model, rev_name, set_delete_handler in rel_model_and_attr:
            if rev_name:
                if rev_name == "+":
                    raise ImproperlyConfigured(
                        f"No backward reference field from {rel_model} to {model}."
                    )
                _registry[_make_registry_key(rel_model, rev_name)] = streamer

                if set_handlers:
                    post_save.connect(handle_post_save, sender=rel_model)
                    if set_delete_handler:
                        post_delete.connect(handle_post_delete, sender=rel_model)
            else:
                m2m_changed.connect(handle_m2m_changed, sender=rel_model)


def get_streamer(model):
    """
    Returns streamer instance for given Django model or None
    """
    return _registry.get(_make_registry_key(model))


def get_registry():
    """
    Returns (model, streamer) tuples for all registered streamer and models
    """
    result = []
    for key, streamer in _registry.items():
        if not key.rel_name:
            model = apps.get_model(key.app_label, key.object_name)
            result.append((model, streamer))
    return result


def get_streamer_for_related(model):
    for_key = _make_registry_key(model)

    for key, streamer in _registry.items():
        if (key.app_label, key.object_name) != (for_key.app_label, for_key.object_name):
            continue
        if not key.rel_name:
            continue

        yield (key.rel_name, streamer)


def autodiscover():
    for config in apps.app_configs.values():
        module_name = config.module.__name__
        try:
            import_module(module_name + ".streamers")
        except ImportError:
            pass
