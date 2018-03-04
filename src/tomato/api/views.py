import datetime
import json
from collections import OrderedDict
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
    ('formats', 'formats'),
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
    ('location_subprovince', 'meetinginfo.location_municipality'),
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


def model_to_json(model, map):
    ret = OrderedDict()
    for to_attr, from_attr in map.items():
        if not from_attr:
            ret[to_attr] = ''
        else:
            item = model
            for attr in from_attr.split('.')[0:-1]:
                item = getattr(model, attr)
            value = getattr(item, from_attr.split('.')[-1])
            if isinstance(value, bool):
                value = '1' if value else '0'
            if isinstance(value, models.Manager):
                value = list(value.all())
                if value and isinstance(value[0], Format):
                    value = ','.join([v.key_string for v in value])
                elif not value:
                    value = ''
            elif value is None:
                value = ''
            else:
                value = str(value)
            ret[to_attr] = value
    return ret


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

    starts_after = parse_time_params(request.GET.get('StartsAfterH'), request.GET.get('StartsAfterM'))
    starts_before = parse_time_params(request.GET.get('StartsBeforeH'), request.GET.get('StartsBeforeM'))
    ends_before = parse_time_params(request.GET.get('EndsBeforeH'), request.GET.get('EndsBeforeM'))

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
    if meeting_key and meeting_key_value:
        if meeting_key in valid_meeting_search_keys:
            model_field = meeting_field_map.get(meeting_key)
            if model_field:
                model_field = model_field.replace('.', '__')
                meeting_qs = meeting_qs.filter(**{model_field: meeting_key_value})
    if starts_after:
        meeting_qs = meeting_qs.filter(start_time__gt=starts_after)
    if starts_before:
        meeting_qs = meeting_qs.filter(start_time__lt=starts_before)
    if ends_before:
        meeting_qs = meeting_qs.annotate(
            end_time=models.ExpressionWrapper(
                models.F('start_time') + models.F('duration'), output_field=models.TimeField()))
        meeting_qs = meeting_qs.filter(end_time__lt=ends_before)
    return meeting_qs


def semantic_query(request, format='json'):
    switcher = request.GET.get('switcher')
    if format != 'json':
        return response.HttpResponseBadRequest()
    if not switcher:
        return response.HttpResponseBadRequest()
    if switcher not in ('GetSearchResults',):
        return response.HttpResponseBadRequest()

    ret = None
    if switcher == 'GetSearchResults':
        meetings = get_search_results(request)
        if format == 'json':
            ret = [model_to_json(m, meeting_field_map) for m in meetings]
            if 'get_used_formats' in request.GET:
                formats = {}
                for meeting in meetings:
                    for format in meeting.formats.all():
                        formats[format.id] = format
                formats = formats.values()
                formats = [model_to_json(f, format_field_map) for f in formats]
                if 'get_formats_only' in request.GET:
                    ret = {'formats': formats}
                else:
                    ret = {'meetings': ret, 'formats': formats}

    return response.HttpResponse(
        json.dumps(ret, separators=(',',':')),
        content_type='application/json'
    )
