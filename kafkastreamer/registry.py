import collections
import logging
from collections.abc import Generator
from importlib import import_module
from typing import Any

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Model
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ForwardOneToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete

from .stream import Streamer

log = logging.getLogger(__name__)

RegistryKey = collections.namedtuple(
    "RegistryKey", ["app_label", "object_name", "rel_name"]
)
_registry: dict[RegistryKey, Streamer] = {}


def _make_registry_key(model: type[Model], rel_name: str | None = None) -> RegistryKey:
    return RegistryKey(
        model._meta.app_label,
        model._meta.object_name,
        rel_name,
    )


def register(
    model: type[Model],
    streamer_class: type[Streamer] | None = None,
    set_handlers: bool = True,
    **kwargs: Any,
) -> Any:
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

    def wrapper(cls: type[Streamer]) -> type[Streamer]:
        register(model, cls)
        return cls

    if streamer_class is None:
        # Called as class decorator
        return wrapper

    log.info(
        f"Registering model {model.__name__} with streamer {streamer_class.__name__}"
    )
    streamer = streamer_class(**kwargs)
    _registry[_make_registry_key(model)] = streamer

    if set_handlers:
        post_save.connect(handle_post_save, sender=model)
        pre_delete.connect(handle_pre_delete, sender=model)
        post_delete.connect(handle_post_delete, sender=model)

    for rel_name in streamer.handle_related or []:
        rel_desc = getattr(model, rel_name)

        rel_model_and_attr: list[tuple[type[Model], str | None, bool]] = []

        if isinstance(rel_desc, ManyToManyDescriptor):
            rel_model_and_attr.append(
                (rel_desc.rel.model, rel_desc.rel.related_name, True)
            )
            if rel_desc.rel.through:
                rel_model_and_attr.append((rel_desc.rel.through, None, True))
            log.debug(
                f"Found {rel_desc.__class__.__name__} relation from"
                f"{model.__name__}({rel_name}) to"
                f" {rel_desc.rel.model.__name__}({rel_desc.rel.related_name})"
            )
        elif isinstance(rel_desc, ReverseManyToOneDescriptor):
            assert isinstance(rel_desc.rel.related_model, type)
            rel_model_and_attr.append(
                (rel_desc.rel.related_model, rel_desc.rel.field.name, True)
            )
            log.debug(
                f"Found {rel_desc.__class__.__name__} relation from"
                f" {model.__name__}({rel_name}) to"
                f" {rel_desc.rel.related_model.__name__}({rel_desc.rel.field.name})"
            )
        elif isinstance(rel_desc, ForwardOneToOneDescriptor):
            set_delete_handler = rel_desc.field.remote_field.on_delete != models.CASCADE
            rel_model_and_attr.append(
                (
                    rel_desc.field.related_model,
                    rel_desc.field.remote_field.name,
                    set_delete_handler,
                )
            )
            log.debug(
                f"Found ({rel_desc.__class__.__name__}) relation from"
                f" {model.__name__}({rel_name}) to"
                f" {rel_desc.field.related_model.__name__}"
                f"({rel_desc.field.remote_field.name})"
            )
        elif isinstance(rel_desc, ForwardManyToOneDescriptor):
            set_delete_handler = rel_desc.field.remote_field.on_delete != models.CASCADE
            rel_model_and_attr.append(
                (
                    rel_desc.field.related_model,
                    rel_desc.field.remote_field.get_accessor_name(),
                    set_delete_handler,
                )
            )
            log.debug(
                f"Found ({rel_desc.__class__.__name__}) relation from"
                f" {model.__name__}({rel_name}) to"
                f" {rel_desc.field.related_model.__name__}"
                f"({rel_desc.field.remote_field.get_accessor_name()})"
            )
        elif isinstance(rel_desc, ReverseOneToOneDescriptor):
            assert isinstance(rel_desc.related.related_model, type)
            rel_model_and_attr.append(
                (rel_desc.related.related_model, rel_desc.related.field.name, True)
            )
            log.debug(
                f"Found ({rel_desc.__class__.__name__}) relation from"
                f" {model.__name__}({rel_name}) to"
                f" {rel_desc.related.related_model.__name__}"
                f"({rel_desc.related.field.name})"
            )
        else:
            raise Exception(f"Unknown relation: {rel_desc}")

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


def get_streamer(model: type[Model]) -> Streamer | None:
    """
    Returns streamer instance for given Django model or None
    """
    return _registry.get(_make_registry_key(model))


def get_registry() -> list[tuple[type[Model], Streamer]]:
    """
    Returns (model, streamer) tuples for all registered streamer and models
    """
    result = []
    for key, streamer in _registry.items():
        if not key.rel_name:
            model = apps.get_model(key.app_label, key.object_name)
            result.append((model, streamer))
    return result


def get_streamer_for_related(
    model: type[Model],
) -> Generator[tuple[str, Streamer], None]:
    for_key = _make_registry_key(model)

    for key, streamer in _registry.items():
        if (key.app_label, key.object_name) != (for_key.app_label, for_key.object_name):
            continue
        if not key.rel_name:
            continue

        yield (key.rel_name, streamer)


def autodiscover() -> None:
    for config in apps.app_configs.values():
        if config.module is None:
            continue
        module_name = config.module.__name__
        try:
            import_module(module_name + ".streamers")
        except ImportError:
            pass
