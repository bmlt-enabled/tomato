from rest_framework import serializers
from . import models


class RootServerSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='rootserver-detail',
        lookup_field='pk',
        lookup_url_kwarg='pk',
    )
    root_server_url = serializers.URLField(source='url')

    class Meta:
        model = models.RootServer
        fields = ('url', 'root_server_url', 'name', 'source_id', 'num_zones', 'num_regions', 'num_areas',
                  'num_meetings', 'num_groups', 'server_info', 'last_successful_import')


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
        model = models.ServiceBody
        fields = ('url', 'root_server', 'parent', 'source_id', 'name', 'type',
                  'description', 'service_body_url', 'world_id', 'num_meetings',
                  'num_groups')


class TranslatedFormatSerializer(serializers.ModelSerializer):
    format = serializers.HyperlinkedRelatedField(
        view_name='format-detail',
        lookup_field='pk',
        read_only=True
    )

    class Meta:
        model = models.TranslatedFormat
        fields = ('url', 'format', 'key_string', 'name', 'description', 'language')


class FormatSerializer(serializers.HyperlinkedModelSerializer):
    root_server = serializers.HyperlinkedRelatedField(
        view_name='rootserver-detail',
        lookup_field='pk',
        read_only=True
    )
    translatedformats = TranslatedFormatSerializer(many=True)

    class Meta:
        model = models.Format
        fields = ('url', 'root_server', 'source_id', 'type', 'world_id', 'translatedformats')


class MeetingInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MeetingInfo
        fields = ('email', 'location_text', 'location_info', 'location_street',
                  'location_city_subsection', 'location_neighborhood', 'location_municipality',
                  'location_sub_province', 'location_province', 'location_postal_code_1',
                  'location_nation', 'train_lines', 'bus_lines', 'world_id', 'comments',
                  'virtual_meeting_link', 'phone_meeting_number', 'virtual_meeting_additional_info')


class MeetingSerializer(serializers.HyperlinkedModelSerializer):
    root_server = serializers.HyperlinkedRelatedField(
        view_name='rootserver-detail',
        lookup_field='pk',
        read_only=True
    )
    service_body = serializers.HyperlinkedRelatedField(
        view_name='servicebody-detail',
        lookup_field='pk',
        read_only=True
    )
    formats = serializers.HyperlinkedModelSerializer
    meetinginfo = MeetingInfoSerializer()

    class Meta:
        model = models.Meeting
        fields = ('url', 'root_server', 'service_body', 'formats', 'source_id', 'name',
                  'weekday', 'start_time', 'duration', 'language', 'latitude', 'longitude',
                  'meetinginfo')
