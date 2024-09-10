from __future__ import absolute_import, unicode_literals

import logging
from collections.abc import Sequence
from typing import Any

from celery import shared_task
from django.apps import apps

import kafkastreamer

log = logging.getLogger(__name__)


@shared_task
def refresh(
    models: Sequence[str] | None = None, source: str | None = None
) -> dict[str, Any]:
    """
    Does full refresh for specified models or all registered models
    """

    if models is None:
        model_classes = [model for model, bus in kafkastreamer.get_registry()]
    else:
        model_classes = [apps.get_model(x) for x in models]

    for model in model_classes:
        model_name = "%s.%s" % (model._meta.app_label, model._meta.object_name)
        refresh_model.delay(model_name=model_name, source=source)

    return {"models_count": len(model_classes)}


@shared_task
def refresh_model(model_name: str, source: str | None = None) -> dict[str, Any]:
    """
    Does full refresh for specified model
    """

    model = apps.get_model(model_name)
    messages_count = kafkastreamer.full_refresh(model)
    log.info(
        "%d messages was send while refreshing model %s.%s",
        messages_count,
        model._meta.app_label,
        model._meta.object_name,
    )

    return {"messages_count": messages_count}
