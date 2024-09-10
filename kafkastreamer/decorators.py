from collections.abc import Callable
from functools import update_wrapper
from typing import Any

from django.contrib.admin import AdminSite
from django.http import HttpRequest

from .context import set_context
from .squashing import squash


def admin_site(source: str) -> Callable[[type[AdminSite]], type[AdminSite]]:
    """
    Decorator function for model admin site class to set streamer context
    and squashing
    """

    def patch_admin_site(admin_site: type[AdminSite]) -> type[AdminSite]:
        orig_admin_view = admin_site.admin_view

        def admin_view(self: AdminSite, view: Callable, cacheable: bool = False) -> Any:
            def inner(request: HttpRequest, *args: Any, **kw: Any) -> Any:
                with set_context(user=request.user, source=source), squash():
                    return view(request, *args, **kw)

            return orig_admin_view(
                self,
                update_wrapper(inner, view),
                cacheable=cacheable,
            )

        admin_site.admin_view = admin_view  # type: ignore
        return admin_site

    def decorator_func(admin_site: type[AdminSite]) -> type[AdminSite]:
        return patch_admin_site(admin_site)

    return decorator_func
