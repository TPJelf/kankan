from django.contrib import admin

from .models import Settings, Task


@admin.register(Settings)
@admin.register(Task)
class UniversalAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        return [field.name for field in self.model._meta.concrete_fields]
