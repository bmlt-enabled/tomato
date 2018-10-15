import datetime
import decimal
from collections import OrderedDict
from django.db import models


def model_has_distance(model):
    if isinstance(model, dict):
        return 'distance' in model
    return hasattr(model, 'distance')


server_info_field_map = OrderedDict([
    ('version',          ('version',),),
    ('versionInt',       ('versionInt',),),
    ('langs',            ('langs',),),
    ('nativeLang',       ('nativeLang',),),
    ('centerLongitude',  ('centerLongitude',),),
    ('centerLatitude',   ('centerLatitude',),),
    ('centerZoom',       ('centerZoom',),),
    ('available_keys',   ('available_keys',),),
    ('changesPerMeeting',('changesPerMeeting',),),
    ('google_api_key',   ('google_api_key',),),
])

service_bodies_field_map = OrderedDict([
    ('id',             ('id',),),
    ('parent_id',      ('calculated_parent_id',),),
    ('name',           ('name',),),
    ('description',    ('description',),),
    ('type',           ('type',),),
    ('url',            ('url',),),
    ('root_server_id', ('root_server_id',),),
    ('helpline',       ('helpline',),),
    ('world_id',       ('world_id',),),
])

format_field_map = OrderedDict([
    ('key_string',         ('key_string',),),
    ('name_string',        ('name',),),
    ('description_string', ('description',),),
    ('lang',               ('language',),),
    ('id',                 ('id',),),
    ('root_server_id',     ('root_server_id',),),
    ('world_id',           ('world_id',),),
    ('root_server_uri',    ('root_server.url',),),
])

meeting_field_map = OrderedDict([
    ('id_bigint',                ('id',),),
    ('worldid_mixed',            ('meetinginfo.world_id',),),
    ('shared_group_id_bigint',   ('',),),
    ('service_body_bigint',      ('service_body.id',),),
    ('weekday_tinyint',          ('weekday',),),
    ('start_time',               ('start_time',),),
    ('duration_time',            ('duration',),),
    ('formats',                  (('formats.key_string', 'formats_aggregate',),),),
    ('lang_enum',                ('language',),),
    ('longitude',                ('longitude',),),
    ('latitude',                 ('latitude',),),
    ('distance_in_km',           (('distance.km',), model_has_distance),),
    ('distance_in_miles',        (('distance.mi',), model_has_distance),),
    ('email_contact',            ('meetinginfo.email',),),
    ('meeting_name',             ('name',),),
    ('location_text',            ('meetinginfo.location_text',),),
    ('location_info',            ('meetinginfo.location_info',),),
    ('location_street',          ('meetinginfo.location_street',),),
    ('location_city_subsection', ('meetinginfo.location_city_subsection',),),
    ('location_neighborhood',    ('meetinginfo.location_neighborhood',),),
    ('location_municipality',    ('meetinginfo.location_municipality',),),
    ('location_sub_province',    ('meetinginfo.location_sub_province',),),
    ('location_province',        ('meetinginfo.location_province',),),
    ('location_postal_code_1',   ('meetinginfo.location_postal_code_1',),),
    ('location_nation',          ('meetinginfo.location_nation',),),
    ('comments',                 ('meetinginfo.comments',),),
    ('train_lines',              ('meetinginfo.train_lines',),),
    ('bus_lines',                ('meetinginfo.bus_lines',),),
    ('contact_phone_2',          ('',),),
    ('contact_email_2',          ('',),),
    ('contact_name_2',           ('',),),
    ('contact_phone_1',          ('',),),
    ('contact_email_1',          ('',),),
    ('contact_name_1',           ('',),),
    ('published',                ('published',),),
    ('root_server_id',           ('root_server_id',),),
    ('root_server_uri',          ('root_server.url',),),
    ('format_shared_id_list',    (('formats.id', 'format_shared_id_list_aggregate',),),),
])

meeting_kml_field_map = OrderedDict([
    ('name',              ('name',),),
    ('address',           ('address',),),
    ('description',       ('description',),),
    ('Point.coordinates', ('coordinates',),),
])

meeting_poi_field_map = OrderedDict([
    ('lon',  ('longitude',),),
    ('lat',  ('latitude',),),
    ('name', ('name',),),
    ('desc', ('description',),),
])

field_keys_with_descriptions = OrderedDict([
    ('id_bigint', 'ID'),
    ('worldid_mixed', 'World ID'),
    ('service_body_bigint', 'Service Body ID'),
    ('weekday_tinyint', 'Weekday'),
    ('start_time', 'Start Time'),
    ('duration_time', 'Duration'),
    ('formats', 'Formats'),
    ('lang_enum', 'Language'),
    ('longitude', 'Longitude'),
    ('latitude', 'Latitude'),
    ('meeting_name', 'Meeting Name'),
    ('location_text', 'Location Name'),
    ('location_info', 'Additional Location Information'),
    ('location_street', 'Street Address'),
    ('location_city_subsection', 'Borough'),
    ('location_neighborhood', 'Neighborhood'),
    ('location_municipality', 'Town'),
    ('location_sub_province', 'County'),
    ('location_province', 'State'),
    ('location_postal_code_1', 'Zip Code'),
    ('location_nation', 'Nation'),
    ('comments', 'Comments'),
    ('train_lines', 'Train Lines'),
    ('bus_lines', 'Bus Lines'),
    ('root_server_id', 'Root Server ID'),
    ('root_server_uri', 'Root Server URI'),
    ('format_shared_id_list', 'Format Shared ID List'),
    ('root_server_uri', 'Root Server URI'),
])

field_keys = list(field_keys_with_descriptions.keys())


def model_get_attr(model, attr):
    def _get_attr(_attr):
        if isinstance(model, dict):
            if '.' in _attr:
                _attr = _attr.replace('.', '__')
            return model.get(_attr)
        item = model
        for a in _attr.split('.')[0:-1]:
            item = getattr(item, a)
        if isinstance(item, models.Manager):
            items = item.all()
            return [getattr(item, _attr.split('.')[-1]) for item in items]
        return getattr(item, _attr.split('.')[-1], None)

    if isinstance(attr, tuple):
        value = _get_attr(attr[0])
        if value is None:
            value = _get_attr(attr[1])
            if value == [None]:
                return []
        return value
    else:
        return _get_attr(attr)


def model_get_value(model, attr):
    if not attr:
        return ''
    else:
        value = model_get_attr(model, attr)
        if isinstance(value, bool):
            value = '1' if value else '0'
        elif isinstance(value, list):
            value = ','.join([str(v) for v in value])
        elif isinstance(value, datetime.timedelta):
            if value.seconds < 36000:
                value = '0' + str(value)
            else:
                value = str(value)
        elif isinstance(value, decimal.Decimal):
            value = str(value).rstrip('0')
        elif value is None:
            value = ''
        else:
            value = str(value)
    return value
