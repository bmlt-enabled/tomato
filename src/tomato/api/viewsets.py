from rest_framework import viewsets
from . import serializers
from .models import RootServer, ServiceBody


class RootServerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RootServer.objects.all()
    serializer_class = serializers.RootServerSerializer


class ServiceBodyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceBody.objects.all()
    serializer_class = serializers.ServiceBodySerializer
