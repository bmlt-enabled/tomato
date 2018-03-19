from rest_framework import viewsets
from . import models, serializers


class RootServerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.RootServer.objects.all()
    serializer_class = serializers.RootServerSerializer


class ServiceBodyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceBody.objects.all()
    serializer_class = serializers.ServiceBodySerializer


class FormatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Format.objects.all()
    serializer_class = serializers.FormatSerializer


class MeetingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Meeting.objects.all()
    serializer_class = serializers.MeetingSerializer
