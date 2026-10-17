from django.contrib import admin

from .models import Farm


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ("farm_name", "user", "latitude", "longitude", "created_at")
    list_filter = ("created_at",)
    search_fields = ("farm_name", "address", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
