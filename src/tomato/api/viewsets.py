from rest_framework import viewsets
from .models import RootServer
from .serializers import RootServerSerializer


class RootServerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RootServer.objects.all()
    serializer_class = RootServerSerializer
