from rest_framework import serializers
from .models import RootServer, ServiceBody


class RootServerSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='rootserver-detail',
        lookup_field='pk',
        lookup_url_kwarg='pk',
    )
    root_server_url = serializers.URLField(source='url')

    class Meta:
        model = RootServer
        fields = ('url', 'root_server_url', 'last_successful_import')


class ServiceBodySerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='servicebody-detail',
        lookup_field='pk'
    )
    root_server = serializers.HyperlinkedRelatedField(
        view_name='rootserver-detail',
        lookup_field='pk',
        read_only=True
    )
    parent = serializers.HyperlinkedRelatedField(
        view_name='servicebody-detail',
        lookup_field='pk',
        read_only=True
    )
    service_body_url = serializers.URLField(source='url')

    class Meta:
        model = ServiceBody
        fields = ('url', 'root_server', 'parent', 'source_id', 'name', 'type',
                  'description', 'service_body_url', 'world_id')
