import json
from collections import OrderedDict
from django.db.models import Q
from django.db.models import Manager
from django.http import response
from .models import Format, Meeting


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


def meeting_to_json(meeting):
    ret = OrderedDict()
    for to_attr, from_attr in meeting_field_map.items():
        if not from_attr:
            ret[to_attr] = ''
        else:
            item = meeting
            for attr in from_attr.split('.')[0:-1]:
                item = getattr(meeting, attr)
            value = getattr(item, from_attr.split('.')[-1])
            if isinstance(value, bool):
                value = '1' if value else '0'
            if isinstance(value, Manager):
                value = list(value.all())
                if value and isinstance(value[0], Format):
                    value = ','.join([v.key_string for v in value])
            else:
                value = str(value)
            if value is None:
                value = ''
            ret[to_attr] = value
    return ret


def get_search_results(request):
    weekdays = request.GET.get('weekdays')
    if weekdays is None:
        weekdays = request.GET.getlist('weekdays[]', [])
    else:
        weekdays = [weekdays]
    weekdays = [int(w) for w in weekdays]
    weekdays_include = [w for w in weekdays if w > 0]
    weekdays_exclude = [abs(w) for w in weekdays if w < 0]

    services = request.GET.get('services')
    if services is None:
        services = request.GET.getlist('services[]', [])
    else:
        services = [services]
    services = [int(s) for s in services]
    services_include = [s for s in services if s > 0]
    services_exclude = [abs(s) for s in services if s < 0]

    formats = request.GET.get('formats')
    if formats is None:
        formats = request.GET.getlist('formats[]', [])
    else:
        formats = [formats]
    formats = [int(f) for f in formats]
    formats_include = [f for f in formats if f > 0]
    formats_exclude = [abs(f) for f in formats if f < 0]

    qs = Meeting.objects.all().prefetch_related('meetinginfo', 'service_body')
    if weekdays_include:
        qs = qs.filter(weekday__in=weekdays_include)
    if weekdays_exclude:
        qs = qs.exclude(weekday__in=weekdays_exclude)
    if services_include:
        qs = qs.filter(service_body_id__in=services_include)
    if services_exclude:
        qs = qs.filter(service_body_id__in=services_exclude)
    if formats_include:
        for id in formats_include:
            qs = qs.filter(Q(formats__id=id))
    if formats_exclude:
        for id in formats_exclude:
            qs = qs.filter(~Q(formats__id=id))


    ret = []
    for meeting in qs:
        ret.append(meeting_to_json(meeting))
    ret = json.dumps(ret)
    return ret


def semantic_query(request, format='json'):
    switcher = request.GET.get('switcher')
    if format != 'json':
        return response.HttpResponseBadRequest()
    if not switcher:
        return response.HttpResponseBadRequest()
    if switcher not in ('GetSearchResults',):
        return response.HttpResponseBadRequest()

    ret = get_search_results(request)

    return response.HttpResponse(ret, content_type='application/json')
