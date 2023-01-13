from functools import update_wrapper

from .context import set_context, squash


def admin_site(source):
    """
    Decorator function for model admin site class to set streamer context
    and squashing
    """

    def patch_admin_site(admin_site):
        orig_admin_view = admin_site.admin_view

        def admin_view(self, view, cacheable=False):
            def inner(request, *args, **kw):
                with set_context(user=request.user, source=source), squash():
                    return view(request, *args, **kw)

            return orig_admin_view(
                self,
                update_wrapper(inner, view),
                cacheable=cacheable,
            )

        admin_site.admin_view = admin_view
        return admin_site

    def decorator_func(admin_site):
        return patch_admin_site(admin_site)

    return decorator_func
