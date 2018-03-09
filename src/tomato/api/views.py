import csv
import datetime
import decimal
import io
import json
import logging
import requests
from collections import OrderedDict
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db import models
from django.http import response
from xml.etree import ElementTree as ET
from .models import Format, Meeting, ServiceBody


logger = logging.getLogger('django')


def model_has_distance(model):
    if isinstance(model, dict):
        return 'distance' in model
    return hasattr(model, 'distance')


service_bodies_field_map = OrderedDict([
    ('id',             ('id',),),
    ('parent_id',      ('parent_id',),),
    ('name',           ('name',),),
    ('description',    ('description',),),
    ('type',           ('type',),),
    ('url',            ('url',),),
    ('helpline',       ('',),),
    ('root_server_id', ('root_server_id',),),
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
])

meeting_field_map = OrderedDict([
    ('id_bigint',                ('id',),),
    ('root_server_id',           ('root_server_id',),),
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
])

valid_meeting_search_keys_with_descriptions = OrderedDict([
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
])

valid_meeting_search_keys = valid_meeting_search_keys_with_descriptions.keys()


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


def model_to_json(model, map, return_attrs=None):
    ret = OrderedDict()
    keys = return_attrs if return_attrs else map.keys()
    for to_attr in keys:
        from_params = map.get(to_attr, None)
        if from_params is None:
            continue
        if len(from_params) > 1:
            qualifier = from_params[1]
            if not qualifier(model):
                continue
        from_attr = from_params[0]
        value = model_get_value(model, from_attr)
        ret[to_attr] = value
    return ret


def model_to_csv(writer, model, map):
    d = {}
    for to_attr in writer.fieldnames:
        from_params = map.get(to_attr, None)
        if from_params is None:
            continue
        if len(from_params) > 1:
            qualifier = from_params[1]
            if not qualifier(model):
                continue
        from_attr = from_params[0]
        value = model_get_value(model, from_attr)
        d[to_attr] = value
    writer.writerow(d)


def model_to_xml(elem, model, map):
    row = ET.SubElement(elem, 'row')
    for to_attr, from_params in map.items():
        if len(from_params) > 1:
            qualifier = from_params[1]
            if not qualifier(model):
                continue
        from_attr = from_params[0]
        value = model_get_value(model, from_attr)
        if value:
            sub = ET.SubElement(row, to_attr)
            sub.text = value
    return row


def models_to_json(models, field_map, return_attrs=None):
    models = [model_to_json(m, field_map, return_attrs=return_attrs) for m in models]
    if getattr(settings, 'DEBUG', False):
        return json.dumps(models, indent=2)
    json.dumps(models, separators=(',', ':'))


def models_to_csv(models, field_map, fieldnames=None):
    if not fieldnames:
        fieldnames = []
        for k, v in field_map.items():
            if len(v) > 1:
                if models:
                    qualifier = v[1]
                    model = models[0]
                    if qualifier(model):
                        fieldnames.append(k)
            else:
                fieldnames.append(k)
    stream = io.StringIO()
    try:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for m in models:
            model_to_csv(writer, m, field_map)
        return stream.getvalue()
    finally:
        stream.close()


def models_to_xml(models, field_map, root_element_name):
    root = ET.Element(root_element_name)
    i = 0
    for m in models:
        row = model_to_xml(root, m, field_map)
        row.set('sequence_index', str(i))
        i += 1
    return ET.tostring(root)


def parse_time_params(hour, minute):
    ret = hour
    if ret:
        if minute:
            ret += ':' + minute
        try:
            ret = [int(t) for t in ret.split(':')]
            ret = datetime.time(*ret)
            ret.replace(tzinfo=datetime.timezone.utc)
        except:
            return None
    return ret


def parse_timedelta_params(hour, minute):
    try:
        if hour and minute:
            return datetime.timedelta(hours=int(hour), minutes=int(minute))
        if hour:
            return datetime.timedelta(hours=int(hour))
        if minute:
            return datetime.timedelta(minutes=int(minute))
    except:
        pass
    return None


def extract_specific_keys_param(GET, key='data_field_key'):
    data_field_keys = GET.get(key)
    if data_field_keys:
        data_field_keys = [k for k in data_field_keys.split(',') if k in valid_meeting_search_keys]
    return data_field_keys


def get_search_results(request):
    weekdays = request.GET.get('weekdays')
    weekdays = request.GET.getlist('weekdays[]', []) if weekdays is None else [weekdays]
    weekdays = [int(w) for w in weekdays]
    weekdays_include = [w for w in weekdays if w > 0]
    weekdays_exclude = [abs(w) for w in weekdays if w < 0]

    services = request.GET.get('services')
    services = request.GET.getlist('services[]', []) if services is None else [services]
    services = [int(s) for s in services]
    services_include = [s for s in services if s > 0]
    services_exclude = [abs(s) for s in services if s < 0]

    formats = request.GET.get('formats')
    formats = request.GET.getlist('formats[]', []) if formats is None else [formats]
    formats = [int(f) for f in formats]
    formats_include = [f for f in formats if f > 0]
    formats_exclude = [abs(f) for f in formats if f < 0]

    root_server_ids = request.GET.get('root_server_ids')
    root_server_ids = request.GET.getlist('root_server_ids[]', []) if root_server_ids is None else [root_server_ids]
    root_server_ids = [int(rs) for rs in root_server_ids]
    root_server_ids_include = [rs for rs in root_server_ids if rs > 0]
    root_server_ids_exclude = [abs(rs) for rs in root_server_ids if rs < 0]

    meeting_key = request.GET.get('meeting_key')
    meeting_key_value = request.GET.get('meeting_key_value')

    data_field_keys = extract_specific_keys_param(request.GET)

    starts_after = parse_time_params(request.GET.get('StartsAfterH'), request.GET.get('StartsAfterM'))
    starts_before = parse_time_params(request.GET.get('StartsBeforeH'), request.GET.get('StartsBeforeM'))
    ends_before = parse_time_params(request.GET.get('EndsBeforeH'), request.GET.get('EndsBeforeM'))
    min_duration = parse_timedelta_params(request.GET.get('MinDurationH'), request.GET.get('MinDurationM'))
    max_duration = parse_timedelta_params(request.GET.get('MaxDurationH'), request.GET.get('MaxDurationM'))

    long_val = request.GET.get('long_val')
    lat_val = request.GET.get('lat_val')
    geo_width = request.GET.get('geo_width')
    geo_width_km = request.GET.get('geo_width_km')
    sort_results_by_distance = request.GET.get('sort_results_by_distance', None) == '1'

    search_string = request.GET.get('SearchString')
    search_string_is_address = request.GET.get('StringSearchIsAnAddress', None) == '1'
    search_string_radius = request.GET.get('SearchStringRadius')
    search_string_all = request.GET.get('SearchStringAll')
    search_string_exact = request.GET.get('SearchStringExact')

    sort_keys = extract_specific_keys_param(request.GET, 'sort_keys')

    meeting_qs = Meeting.objects.all()
    meeting_qs = meeting_qs.prefetch_related('meetinginfo', 'service_body', 'formats')

    if weekdays_include:
        meeting_qs = meeting_qs.filter(weekday__in=weekdays_include)
    if weekdays_exclude:
        meeting_qs = meeting_qs.exclude(weekday__in=weekdays_exclude)
    if services_include:
        meeting_qs = meeting_qs.filter(service_body_id__in=services_include)
    if services_exclude:
        meeting_qs = meeting_qs.exclude(service_body_id__in=services_exclude)
    if formats_include:
        for id in formats_include:
            meeting_qs = meeting_qs.filter(models.Q(formats__id=id))
    if formats_exclude:
        for id in formats_exclude:
            meeting_qs = meeting_qs.filter(~models.Q(formats__id=id))
    if root_server_ids_include:
        meeting_qs = meeting_qs.filter(root_server_id__in=root_server_ids_include)
    if root_server_ids_exclude:
        meeting_qs = meeting_qs.exclude(root_server_id__in=root_server_ids_exclude)
    if meeting_key and meeting_key_value:
        if meeting_key in valid_meeting_search_keys:
            model_field = meeting_field_map.get(meeting_key)[0]
            if isinstance(model_field, tuple):
                model_field = model_field[0]
            if model_field:
                model_field = model_field.replace('.', '__')
                meeting_qs = meeting_qs.filter(**{model_field: meeting_key_value})
    if starts_after:
        meeting_qs = meeting_qs.filter(start_time__gt=starts_after)
    if starts_before:
        meeting_qs = meeting_qs.filter(start_time__lt=starts_before)
    if ends_before: 
        exp = models.F('start_time') + models.F('duration')
        exp_wrapper = models.ExpressionWrapper(exp, output_field=models.TimeField())
        meeting_qs = meeting_qs.annotate(end_time=exp_wrapper)
        meeting_qs = meeting_qs.filter(end_time__lt=ends_before)
    if min_duration:
        meeting_qs = meeting_qs.filter(duration__gte=min_duration)
    if max_duration:
        meeting_qs = meeting_qs.filter(duration__lte=max_duration)
    if data_field_keys:
        values = []
        for key in data_field_keys:
            model_field = meeting_field_map.get(key)[0]
            if isinstance(model_field, tuple):
                field_name = model_field[0].replace('.', '__')
                agg_name = model_field[1]
                meeting_qs = meeting_qs.annotate(**{agg_name: ArrayAgg(field_name)})
                values.append(agg_name)
            elif model_field:
                model_field = model_field.replace('.', '__')
                values.append(model_field)
        meeting_qs = meeting_qs.values(*values)
    if (long_val and lat_val and (geo_width or geo_width_km)) or (search_string and search_string_is_address):
        try:
            get_nearest = False
            if search_string and search_string_is_address:
                # Translate address to lat/long using geocode api
                url = 'https://maps.googleapis.com/maps/api/geocode/json?key={}&address={}&sensor=false'
                r = requests.get(url.format(settings.GOOGLE_MAPS_API_KEY, search_string))
                if r.status_code != 200:
                    logger.warning('Received bad status code {} from geocode api request {}'.format(r.status_code, url))
                r = json.loads(r.content)
                if r['status'] != 'OK':
                    logger.warning('Received bad status {} from geocode api request: {}'.format(r['status'], url))
                latitude = r['results'][0]['geometry']['location']['lat']
                longitude = r['results'][0]['geometry']['location']['lng']
                get_nearest = 10
            else:
                latitude = float(lat_val)
                longitude = float(long_val)
                if geo_width is not None:
                    geo_width = float(geo_width)
                    if geo_width < 0:
                        get_nearest = abs(int(geo_width))
                elif geo_width_km is not None:
                    geo_width_km = float(geo_width_km)
                    if geo_width_km < 0:
                        get_nearest = abs(int(geo_width_km))
            point = Point(x=longitude, y=latitude, srid=4326)
        except:
            pass
        else:
            meeting_qs = meeting_qs.annotate(distance=Distance('point', point))
            if get_nearest:
                qs = meeting_qs.order_by('distance').values_list('id')
                meeting_ids = [m[0] for m in qs[:get_nearest]]
                meeting_qs = meeting_qs.filter(id__in=meeting_ids)
            else:
                d = geo_width if geo_width is not None else geo_width_km
                d = D(mi=d) if geo_width is not None else D(km=d)
                meeting_qs = meeting_qs.filter(point__distance_lte=(point, d))
            if sort_results_by_distance:
                meeting_qs = meeting_qs.order_by('distance')
    if sort_keys and not sort_results_by_distance:
        values = []
        for key in sort_keys:
            model_field = meeting_field_map.get(key)[0]
            if model_field:
                if isinstance(model_field, tuple):
                    continue  # no sorting by many to many relationships
                model_field = model_field.replace('.', '__')
                values.append(model_field)
        meeting_qs = meeting_qs.order_by(*values)
    return meeting_qs


def get_field_values(request):
    root_server_id = request.GET.get('root_server_id')
    meeting_key = request.GET.get('meeting_key')
    meeting_qs = Meeting.objects.all()
    if root_server_id:
        meeting_qs = Meeting.objects.filter(root_server_id=root_server_id)
    if meeting_key in valid_meeting_search_keys:
        model_field = meeting_field_map.get(meeting_key)[0]
        if isinstance(model_field, tuple):
            model_field = model_field[0]
        if model_field:
            model_field = model_field.replace('.', '__')
            meeting_qs = meeting_qs.values(model_field)
            meeting_qs = meeting_qs.annotate(ids=ArrayAgg('id'))
    return meeting_qs


def get_formats(request):
    root_server_id = request.GET.get('root_server_id')
    format_qs = Format.objects.all()
    if root_server_id:
        format_qs = format_qs.filter(root_server_id=root_server_id)
    return format_qs


def get_service_bodies(request):
    root_server_id = request.GET.get('root_server_id')
    body_qs = ServiceBody.objects.all()
    if root_server_id:
        body_qs = body_qs.filter(root_server_id=root_server_id)
    return body_qs


def semantic_query(request, format='json'):
    switcher = request.GET.get('switcher')
    if format not in ('csv', 'json', 'xml'):
        return response.HttpResponseBadRequest()
    if not switcher:
        return response.HttpResponseBadRequest()
    if switcher not in ('GetSearchResults', 'GetFormats', 'GetServiceBodies', 'GetFieldKeys', 'GetFieldValues'):
        return response.HttpResponseBadRequest()

    ret = None
    if format == 'json':
        content_type = 'application/json'
    elif format == 'csv':
        content_type = 'text/csv'
    elif format == 'xml':
        content_type = 'application/xml'

    if switcher == 'GetSearchResults':
        meetings = get_search_results(request)
        data_field_keys = extract_specific_keys_param(request.GET)
        if format == 'json':
            kwargs = {}
            if data_field_keys:
                kwargs['return_attrs'] = data_field_keys
            if 'get_used_formats' in request.GET:
                formats = Format.objects.filter(id__in=meetings.values('formats'))
                formats = [model_to_json(f, format_field_map) for f in formats]
                if 'get_formats_only' in request.GET:
                    ret = {'formats': formats}
                else:
                    meetings = [model_to_json(m, meeting_field_map, **kwargs) for m in meetings]
                    ret = {'meetings': meetings, 'formats': formats}
                if getattr(settings, 'DEBUG', False):
                    ret = json.dumps(ret, indent=2)
                else:
                    ret = json.dumps(ret, separators=(',', ':'))
            else:
                ret = models_to_json(meetings, meeting_field_map, return_attrs=data_field_keys)
        elif format == 'csv':
            ret = models_to_csv(meetings, meeting_field_map, data_field_keys)
        elif format == 'xml':
            ret = models_to_xml(meetings, meeting_field_map, 'meetings')
    else:
        if switcher == 'GetFormats':
            models = get_formats(request)
            field_map = format_field_map
            xml_node_name = 'formats'
        elif switcher == 'GetServiceBodies':
            models = get_service_bodies(request)
            field_map = service_bodies_field_map
            xml_node_name = 'serviceBodies'
        elif switcher == 'GetFieldKeys':
            models = [{'key': k, 'description': d} for k, d in valid_meeting_search_keys_with_descriptions.items()]
            field_map = {'key': ('key',), 'description': ('description',)}
            xml_node_name = 'fields'
        elif switcher == 'GetFieldValues':
            meeting_key = request.GET.get('meeting_key')
            if meeting_key in valid_meeting_search_keys:
                models = get_field_values(request)
                field_map = {meeting_key: (meeting_field_map.get(meeting_key)[0],), 'ids': ('ids',)}
                xml_node_name = 'fields'
            else:
                return response.HttpResponseBadRequest()

        if format == 'json':
            ret = models_to_json(models, field_map)
        elif format == 'csv':
            ret = models_to_csv(models, field_map)
        elif format == 'xml':
            ret = models_to_xml(models, field_map, xml_node_name)

    return response.HttpResponse(ret, content_type=content_type)
