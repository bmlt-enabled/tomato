from django.contrib import admin
from .models import ImportProblem, RootServer, ServiceBody, Format, Meeting, MeetingInfo


class RootServerAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'last_successful_import')
    search_fields = ('id', 'url')


class ServiceBodyAdmin(admin.ModelAdmin):
    list_display = ('id', 'root_server', 'name', 'type')
    search_fields = ('id', 'name', 'type', 'world_id', 'root_server__url')


class MeetingAdmin(admin.ModelAdmin):
    list_display = ('id', 'root_server', 'service_body_id', 'service_body', 'name')
    search_fields = ('id', 'name', 'meetinginfo__world_id', 'service_body__name', 'root_server__url')


class ImportProblemAdmin(admin.ModelAdmin):
    list_display = ('id', 'root_server', 'message')
    search_fields = ('message', 'data', 'root_server__url')


admin.site.register(RootServer, RootServerAdmin)
admin.site.register(ServiceBody, ServiceBodyAdmin)
admin.site.register(Format)
admin.site.register(Meeting, MeetingAdmin)
admin.site.register(MeetingInfo)
admin.site.register(ImportProblem, ImportProblemAdmin)
