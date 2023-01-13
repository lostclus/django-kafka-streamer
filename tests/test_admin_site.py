from unittest import mock

from django.contrib import admin
from django.http import HttpResponse
from django.test.client import RequestFactory

from kafkastreamer.context import _context


def test_admin_view():
    def test_view_se(request):
        assert _context.source == "admin"
        assert _context.user.pk == 123
        assert _context.squash is not None
        return HttpResponse()

    test_view = mock.MagicMock()
    test_view.side_effect = test_view_se

    admin_view = admin.site.admin_view(test_view)

    rf = RequestFactory()
    request = rf.get("/")
    request.user = mock.MagicMock()
    request.user.is_authenticated.return_value = True
    request.user.pk = 123

    admin_view(request)

    test_view.assert_called_once()
