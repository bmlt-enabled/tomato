import csv
import datetime
import decimal
import json
import io
from collections import OrderedDict
from django.conf import settings
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db import models
from django.http import response
from .models import Format, Meeting


format_field_map = OrderedDict([
    ('key_string', 'key_string'),
    ('name_string', 'name'),
    ('description_string', 'description'),
    ('lang', 'language'),
    ('id', 'id'),
    ('world_id', 'world_id'),
])

meeting_field_map = OrderedDict([
    ('id_bigint', 'id'),
    ('worldid_mixed', 'meetinginfo.world_id'),
    ('shared_group_id_bigint', ''),
    ('service_body_bigint', 'service_body.id'),
    ('weekday_tinyint', 'weekday'),
    ('start_time', 'start_time'),
    ('duration_time', 'duration'),
    ('formats', ('formats.key_string', 'formats_aggregate'),),
    ('lang_enum', 'language'),
    ('longitude', 'longitude'),
    ('latitude', 'latitude'),
    ('distance_in_km', ''),
    ('distance_in_miles', ''),
    ('email_contact', 'meetinginfo.email'),
    ('meeting_name', 'name'),
    ('location_text', 'meetinginfo.location_text'),
    ('location_info', 'meetinginfo.location_info'),
    ('location_street', 'meetinginfo.location_street'),
    ('location_city_subsection', 'meetinginfo.location_city_subsection'),
    ('location_neighborhood', 'meetinginfo.location_neighborhood'),
    ('location_municipality', 'meetinginfo.location_municipality'),
    ('location_sub_province', 'meetinginfo.location_sub_province'),
    ('location_province', 'meetinginfo.location_province'),
    ('location_postal_code_1', 'meetinginfo.location_postal_code_1'),
    ('location_nation', 'meetinginfo.location_nation'),
    ('comments', 'meetinginfo.comments'),
    ('train_lines', 'meetinginfo.train_lines'),
    ('bus_lines', 'meetinginfo.bus_lines'),
    ('contact_phone_2', 'meetinginfo.contact_phone_2'),
    ('contact_email_2', 'meetinginfo.contact_email_2'),
    ('contact_name_2', 'meetinginfo.contact_name_2'),
    ('contact_phone_1', 'meetinginfo.contact_phone_1'),
    ('contact_email_1', 'meetinginfo.contact_email_1'),
    ('contact_name_1', 'meetinginfo.contact_name_1'),
    ('published', 'published'),
])

valid_meeting_search_keys = [
     'worldid_mixed',
     'start_time',
     'duration_time',
     'lang_enum',
     'meeting_name',
     'location_text',
     'location_info',
     'location_street',
     'location_city_subsection',
     'location_neighborhood',
     'location_municipality',
     'location_sub_province',
     'location_province',
     'location_postal_code_1',
     'location_nation',
     'comments',
     'train_lines',
     'bus_lines',
]

valid_specific_fields_keys = [
    'id_bigint',
    'worldid_mixed',
    'service_body_bigint',
    'weekday_tinyint',
    'start_time',
    'duration_time',
    'formats',
    'lang_enum',
    'longitude',
    'latitude',
    'distance_in_km',
    'distance_in_miles',
    'email_contact',
    'meeting_name',
    'location_text',
    'location_info',
    'location_street',
    'location_city_subsection',
    'location_neighborhood',
    'location_municipality',
    'location_sub_province',
    'location_province',
    'location_postal_code_1',
    'location_nation',
    'comments',
    'train_lines',
    'bus_lines',
    'contact_phone_2',
    'contact_email_2',
    'contact_name_2',
    'contact_phone_1',
    'contact_email_1',
    'contact_name_1',
    'published',
]


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
            value = ','.join(value)
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
        from_attr = map.get(to_attr, None)
        if from_attr is None:
            continue
        value = model_get_value(model, from_attr)
        ret[to_attr] = value
    return ret


def model_to_csv(writer, model, map):
    d = {}
    for to_attr in writer.fieldnames:
        from_attr = map.get(to_attr, None)
        if from_attr is None:
            continue
        value = model_get_value(model, from_attr)
        d[to_attr] = value
    writer.writerow(d)


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
        data_field_keys = [k.strip() for k in data_field_keys.split(',')]
        data_field_keys = [k for k in data_field_keys if k in valid_specific_fields_keys]
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

    meeting_key = request.GET.get('meeting_key')
    meeting_key_value = request.GET.get('meeting_key_value')

    data_field_keys = extract_specific_keys_param(request.GET)

    starts_after = parse_time_params(request.GET.get('StartsAfterH'), request.GET.get('StartsAfterM'))
    starts_before = parse_time_params(request.GET.get('StartsBeforeH'), request.GET.get('StartsBeforeM'))
    ends_before = parse_time_params(request.GET.get('EndsBeforeH'), request.GET.get('EndsBeforeM'))
    min_duration = parse_timedelta_params(request.GET.get('MinDurationH'), request.GET.get('MinDurationM'))
    max_duration = parse_timedelta_params(request.GET.get('MaxDurationH'), request.GET.get('MaxDurationM'))

    sort_keys = extract_specific_keys_param(request.GET, 'sort_keys')

    meeting_qs = Meeting.objects.all()
    meeting_qs = meeting_qs.prefetch_related('meetinginfo', 'service_body', 'formats')
    #meeting_qs = meeting_qs.filter(root_server__url='http://www.grscnabmlt.tk/main_server/')
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
    if meeting_key and meeting_key_value:
        if meeting_key in valid_meeting_search_keys:
            model_field = meeting_field_map.get(meeting_key)
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
            model_field = meeting_field_map.get(key)
            if isinstance(model_field, tuple):
                field_name = model_field[0].replace('.', '__')
                agg_name = model_field[1]
                meeting_qs = meeting_qs.annotate(**{agg_name: ArrayAgg(field_name)})
                values.append(agg_name)
            elif model_field:
                model_field = model_field.replace('.', '__')
                values.append(model_field)
        meeting_qs = meeting_qs.values(*values)
    if sort_keys:
        values = []
        for key in sort_keys:
            model_field = meeting_field_map.get(key)
            if model_field:
                if isinstance(model_field, tuple):
                    continue  # no sorting by many to many relationships
                model_field = model_field.replace('.', '__')
                values.append(model_field)
        meeting_qs = meeting_qs.order_by(*values)
    return meeting_qs


def semantic_query(request, format='json'):
    switcher = request.GET.get('switcher')
    if format not in ('csv', 'json'):
        return response.HttpResponseBadRequest()
    if not switcher:
        return response.HttpResponseBadRequest()
    if switcher not in ('GetSearchResults',):
        return response.HttpResponseBadRequest()

    ret = None
    content_type = 'text/html'
    if switcher == 'GetSearchResults':
        meetings = get_search_results(request)
        if format == 'json':
            content_type = 'application/json'
            kwargs = {}
            data_field_keys = extract_specific_keys_param(request.GET)
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
            else:
                ret = [model_to_json(m, meeting_field_map, **kwargs) for m in meetings]

            if getattr(settings, 'DEBUG', False):
                # no harm in making the json a little more readable in debug mode
                ret = json.dumps(ret, indent=2)
            else:
                ret = json.dumps(ret, separators=(',', ':'))
        elif format == 'csv':
            content_type = 'text/csv'
            data_field_keys = extract_specific_keys_param(request.GET)
            if not data_field_keys:
                data_field_keys = meeting_field_map.keys()
            stream = io.StringIO()
            try:
                writer = csv.DictWriter(stream, fieldnames=data_field_keys, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                for m in meetings:
                    model_to_csv(writer, m, meeting_field_map)
                ret = stream.getvalue()
            finally:
                stream.close()

    return response.HttpResponse(ret, content_type=content_type)
