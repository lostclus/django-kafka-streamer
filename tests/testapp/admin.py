from django.contrib import admin

import kafkastreamer
from tests.testapp.models import ModelA


@admin.register(ModelA)
class ModelAAdmin(admin.ModelAdmin):
    pass


@kafkastreamer.admin_site(source="admin")
class AdminSite(admin.AdminSite):
    pass


admin.site = AdminSite()
