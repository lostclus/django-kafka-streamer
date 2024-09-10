from collections.abc import Generator
from contextlib import contextmanager
from threading import local

from django.db.models import Model

from .types import User

_context = local()


@contextmanager
def set_context(
    user: User | None = None,
    source: str | None = None,
) -> Generator[None, None]:
    """
    Context manager to setting message streamer context variables
    """
    _context.user = user
    _context.source = source
    yield
    _context.user = None
    _context.source = None


@contextmanager
def stop_handlers(*models: type[Model]) -> Generator[None, None]:
    """
    Context manager to stop handlers for particular or all models
    """
    _context.stop_handlers = set(models)
    yield
    _context.stop_handlers = None


def is_model_handler_stopped(model: type[Model]) -> bool:
    models = getattr(_context, "stop_handlers", None)
    if models is None:
        return False
    return not models or model in models
