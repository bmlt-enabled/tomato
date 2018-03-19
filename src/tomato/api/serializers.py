from rest_framework import serializers
from .models import RootServer


class RootServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = RootServer
        fields = ('id', 'url', 'last_successful_import')
