from django.contrib import admin
from .models import ImportProblem, RootServer, ServiceBody, Format, Meeting, MeetingInfo


admin.site.register(RootServer)
admin.site.register(ServiceBody)
admin.site.register(Format)
admin.site.register(Meeting)
admin.site.register(MeetingInfo)
admin.site.register(ImportProblem)
