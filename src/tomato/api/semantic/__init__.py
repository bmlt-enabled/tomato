import datetime
import decimal
import logging
import threading
from collections import OrderedDict
from contextlib import contextmanager
from django.db import models
from ..models import RootServer, ServiceBody, TranslatedFormat


logger = logging.getLogger('django')


def model_has_distance(model):
    if isinstance(model, dict):
        return 'distance' in model
    return hasattr(model, 'distance')


def get_naws_dump_area_region_world_id(model):
    sb = model.service_body
    if sb.type in (ServiceBody.AREA, ServiceBody.REGION) and sb.world_id:
        return sb.world_id
    return ''


def get_naws_dump_parent_name(model):
    sb = model.service_body
    while sb:
        if sb.type in (ServiceBody.AREA, ServiceBody.REGION):
            return sb.name
        sb = sb.parent
    return ''


def get_naws_dump_open_or_closed(model):
    if model.formats.filter(world_id='OPEN').exists():
        return 'OPEN'
    return 'CLOSED'


def get_naws_dump_wheelchair(model):
    if model.formats.filter(world_id='WCHR').exists():
        return 'TRUE'
    return 'FALSE'


def get_naws_dump_day(model):
    days = [None, 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    return days[model.weekday]


def get_naws_dump_time(model):
    return ''.join(str(model.start_time).split(':')[0:2])


def get_naws_dump_language(model):
    if model.formats.filter(world_id='LANG').exists():
        return model.formats.filter(world_id='LANG').first().key_string
    return ''


def get_naws_dump_format(model, format_num):
    formats = model.formats.exclude(world_id__in=['OPEN', 'CLOSED', 'WCHR'])
    formats = formats.filter(world_id__isnull=False)
    formats = formats.exclude(world_id='')
    formats = formats.order_by('world_id')
    if formats:
        if len(formats) >= format_num:
            return formats[format_num - 1].world_id
    return ''


def get_naws_dump_format1(model):
    return get_naws_dump_format(model, 1)


def get_naws_dump_format2(model):
    return get_naws_dump_format(model, 2)


def get_naws_dump_format3(model):
    return get_naws_dump_format(model, 3)


def get_naws_dump_format4(model):
    return get_naws_dump_format(model, 4)


def get_naws_dump_format5(model):
    return get_naws_dump_format(model, 5)


def get_naws_dump_city(model):
    if model.meetinginfo.location_city_subsection is not None:
        ret = model.meetinginfo.location_city_subsection.strip()
        if ret:
            return ret
    if model.meetinginfo.location_municipality is not None:
        ret = model.meetinginfo.location_municipality.strip()
        if ret:
            return ret
    if model.meetinginfo.location_neighborhood is not None:
        return model.meetinginfo.location_neighborhood.strip()
    return ''


def get_naws_dump_institutional(model):
    return 'FALSE'


def get_naws_dump_deleted(model):
    if model.deleted:
        return 'D'
    return ''


def get_naws_dump_last_changed(model):
    return ''


def get_naws_dump_unpublished(model):
    if not model.published:
        return '1'
    return ''


formats_cache_timestamp: datetime.datetime = None
language_by_thread: dict[int, str] = {}
formats_by_language = None


@contextmanager
def translated_formats_context(language):
    global formats_cache_timestamp
    global formats_by_language
    global language_by_thread

    last_import_timestamp: datetime.datetime = RootServer.objects.values_list("last_successful_import", flat=True).order_by("-last_successful_import").first()
    if formats_by_language is None or formats_cache_timestamp is None or (last_import_timestamp and last_import_timestamp > formats_cache_timestamp):
        logger.error("populating formats cache")
        formats_qs = TranslatedFormat.objects.filter()
        formats_qs = formats_qs.select_related('format')
        _formats_by_language = {}
        for format in formats_qs:
            if format.language not in _formats_by_language:
                _formats_by_language[format.language] = {}
            if format.format.id not in _formats_by_language[format.language]:
                _formats_by_language[format.language][format.format.id] = format
        formats_by_language = _formats_by_language
        formats_cache_timestamp = last_import_timestamp

    thread_id = threading.get_ident()
    language_by_thread[thread_id] = language

    try:
        yield
    finally:
        try:
            del language_by_thread[thread_id]
        except KeyError:
            pass


def get_formats_key_strings(model):
    thread_id = threading.get_ident()
    current_formats_language = language_by_thread.get(thread_id, 'en')
    desired_language_formats = formats_by_language.get(current_formats_language, dict())
    default_language_formats = formats_by_language.get('en', dict())
    ret = []
    for format in model.formats.all():
        translated_format = desired_language_formats.get(format.id)
        if not translated_format:
            translated_format = default_language_formats.get(format.id)
        if translated_format:
            ret.append(translated_format.key_string)
    return ','.join(ret)


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
    ('id',                 ('format.id',),),
    ('root_server_id',     ('format.root_server_id',),),
    ('world_id',           ('format.world_id',),),
    ('root_server_uri',    ('format.root_server.url',),),
    ('format_type_enum',   ('format.type', lambda m: m.format.type is not None,),),
])

naws_dump_field_map = OrderedDict([
    ('Committee', ('meetinginfo.world_id',),),
    ('CommitteeName', ('name',),),
    ('AddDate', ('',),),
    ('AreaRegion', (get_naws_dump_area_region_world_id,),),
    ('ParentName', (get_naws_dump_parent_name,),),
    ('ComemID', ('',),),
    ('ContactID', ('',),),
    ('ContactName', ('',),),
    ('CompanyName', ('',),),
    ('ContactAddrID', ('',),),
    ('ContactAddress1', ('',),),
    ('ContactAddress2', ('',),),
    ('ContactCity', ('',),),
    ('ContactState', ('',),),
    ('ContactZip', ('',),),
    ('ContactCountry', ('',),),
    ('ContactPhone', ('',),),
    ('MeetingID', ('',),),
    ('Room', ('',),),
    ('Closed', (get_naws_dump_open_or_closed,),),
    ('WheelChr', (get_naws_dump_wheelchair,),),
    ('Day', (get_naws_dump_day,),),
    ('Time', (get_naws_dump_time,),),
    ('Language1', (get_naws_dump_language,),),
    ('Language2', ('',),),
    ('Language3', ('',),),
    ('LocationId', ('',),),
    ('Place', ('meetinginfo.location_text',),),
    ('Address', ('meetinginfo.location_street',),),
    ('City', (get_naws_dump_city,),),
    ('LocBorough', ('meetinginfo.location_neighborhood',),),
    ('State', ('meetinginfo.location_province',),),
    ('Zip', ('meetinginfo.location_postal_code_1',),),
    ('Country', ('meetinginfo.location_nation',),),
    ('Directions', ('meetinginfo.location_info',),),
    ('Institutional', (get_naws_dump_institutional,),),
    ('Format1', (get_naws_dump_format1,),),
    ('Format2', (get_naws_dump_format2,),),
    ('Format3', (get_naws_dump_format3,),),
    ('Format4', (get_naws_dump_format4,),),
    ('Format5', (get_naws_dump_format5,),),
    ('Delete', (get_naws_dump_deleted,),),
    ('LastChanged', (get_naws_dump_last_changed,),),
    ('Longitude', ('longitude',),),
    ('Latitude', ('latitude',),),
    ('ContactGP', ('',),),
    ('bmlt_id', ('id',),),
    ('unpublished', (get_naws_dump_unpublished,),),
])

meeting_field_map = OrderedDict([
    ('id_bigint',                       ('id',),),
    ('worldid_mixed',                   ('meetinginfo.world_id',),),
    ('shared_group_id_bigint',          ('',),),
    ('service_body_bigint',             ('service_body.id',),),
    ('weekday_tinyint',                 ('weekday',),),
    ('venue_type',                      ('venue_type',),),
    ('start_time',                      ('start_time',),),
    ('duration_time',                   ('duration',),),
    ('formats',                         (get_formats_key_strings,),),
    ('lang_enum',                       ('language',),),
    ('longitude',                       ('longitude',),),
    ('latitude',                        ('latitude',),),
    ('distance_in_km',                  (('distance.km',), model_has_distance),),
    ('distance_in_miles',               (('distance.mi',), model_has_distance),),
    ('email_contact',                   ('meetinginfo.email',),),
    ('meeting_name',                    ('name',),),
    ('location_text',                   ('meetinginfo.location_text',),),
    ('location_info',                   ('meetinginfo.location_info',),),
    ('location_street',                 ('meetinginfo.location_street',),),
    ('location_city_subsection',        ('meetinginfo.location_city_subsection',),),
    ('location_neighborhood',           ('meetinginfo.location_neighborhood',),),
    ('location_municipality',           ('meetinginfo.location_municipality',),),
    ('location_sub_province',           ('meetinginfo.location_sub_province',),),
    ('location_province',               ('meetinginfo.location_province',),),
    ('location_postal_code_1',          ('meetinginfo.location_postal_code_1',),),
    ('location_nation',                 ('meetinginfo.location_nation',),),
    ('comments',                        ('meetinginfo.comments',),),
    ('train_lines',                     ('meetinginfo.train_lines',),),
    ('bus_lines',                       ('meetinginfo.bus_lines',),),
    ('virtual_meeting_link',            ('meetinginfo.virtual_meeting_link',),),
    ('phone_meeting_number',            ('meetinginfo.phone_meeting_number',),),
    ('virtual_meeting_additional_info', ('meetinginfo.virtual_meeting_additional_info',),),
    ('contact_phone_2',                 ('',),),
    ('contact_email_2',                 ('',),),
    ('contact_name_2',                  ('',),),
    ('contact_phone_1',                 ('',),),
    ('contact_email_1',                 ('',),),
    ('contact_name_1',                  ('',),),
    ('published',                       ('published',),),
    ('root_server_id',                  ('root_server_id',),),
    ('root_server_uri',                 ('root_server.url',),),
    ('format_shared_id_list',           (('formats.id', 'format_shared_id_list_aggregate',),),),
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
    ('venue_type', 'Venue Type'),
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
    ('virtual_meeting_link', 'Virtual Meeting Link'),
    ('phone_meeting_number', 'Phone Meeting Dial-in Number'),
    ('virtual_meeting_additional_info', 'Virtual Meeting Additional Information'),
    ('root_server_id', 'Root Server ID'),
    ('root_server_uri', 'Root Server URI'),
    ('format_shared_id_list', 'Format Shared ID List'),
])

distance_field_keys = ['distance_in_miles', 'distance_in_km']
field_keys = list(field_keys_with_descriptions.keys()) + distance_field_keys


def model_get_attr(model, attr, related_models_filter_function=None):
    def _get_attr(_attr):
        if isinstance(model, dict):
            if '.' in _attr:
                if _attr.startswith('distance.'):
                    distance = model.get('distance')
                    return getattr(distance, _attr.split('.')[1])
                else:
                    _attr = _attr.replace('.', '__')
            return model.get(_attr)
        item = model
        for a in _attr.split('.')[0:-1]:
            if isinstance(item, models.Manager) or isinstance(item, models.QuerySet):
                item = [getattr(item, a).filter() for item in item.filter()]
            else:
                item = getattr(item, a)
        if isinstance(item, models.Manager):
            items = related_models_filter_function(item) if related_models_filter_function else item.filter()
            return [getattr(item, _attr.split('.')[-1]) for item in items]
        elif isinstance(item, list):
            ret = []
            items = item
            for item in items:
                ret.extend([
                    getattr(_item, _attr.split('.')[-1])
                    for _item in (related_models_filter_function(item) if related_models_filter_function else item.filter())
                ])
            return ret
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


def model_get_value(model, attr, related_models_filter_function=None):
    if not attr:
        return ''
    elif callable(attr):
        value = attr(model)
    else:
        value = model_get_attr(model, attr, related_models_filter_function=related_models_filter_function)
    if isinstance(value, bool):
        value = '1' if value else '0'
    elif isinstance(value, list):
        value = ','.join({str(v) for v in value})
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
