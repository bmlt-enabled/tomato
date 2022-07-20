import datetime
import json
import itertools
import logging
import requests
import sys
import textwrap
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db import models
from django.db.models import F, Q, Window
from django.db.models.functions import Concat
from django.db.models.expressions import Case, When, Value
from django.http import response
from django.template.loader import render_to_string
from .kml import apply_kml_annotations
from .models import TranslatedFormat, Meeting, ServiceBody
from .semantic import (field_keys, field_keys_with_descriptions, format_field_map, meeting_field_map,
                       meeting_poi_field_map, meeting_kml_field_map, server_info_field_map, service_bodies_field_map,
                       naws_dump_field_map, distance_field_keys, set_thread_language)
from .semantic.csv import models_to_csv
from .semantic.json import models_to_json
from .semantic.xml import models_to_xml


logger = logging.getLogger('django')


class GeocodeAPIException(Exception):
    pass


class JSONPStreamingHttpResponse(response.StreamingHttpResponse):
    def __init__(self, *args, **kwargs):
        self.callback = kwargs.pop('callback')
        super().__init__(*args, **kwargs)

    @response.StreamingHttpResponse.streaming_content.setter
    def streaming_content(self, value):
        value = itertools.chain(self.callback + '(', value, ')')
        response.StreamingHttpResponse.streaming_content.fset(self, value)


keys_not_searchable = [
    'id_bigint',
    'service_body_bigint',
    'weekday_tinyint',
    'formats',
    'longitude',
    'latitude',
    'format_shared_id_list',
    'distance_in_km',
    'distance_in_miles',
]

valid_meeting_search_keys = [f for f in field_keys if f not in keys_not_searchable]


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


def extract_specific_keys_param(GET, key='data_field_key', exclude=list()):
    data_field_keys = GET.get(key)
    if data_field_keys:
        data_field_keys = [k for k in data_field_keys.split(',') if k in field_keys and k not in exclude]
    return data_field_keys


def address_to_coordinates(address):
    # Translate address to lat/long using geocode api
    url = 'https://maps.googleapis.com/maps/api/geocode/json?key={}&address={}&sensor=false'
    r = requests.get(url.format(settings.GOOGLE_MAPS_API_KEY, address))
    if r.status_code != 200:
        message = 'Received bad status code {} from geocode api request {}'.format(r.status_code, url)
        logger.error(message)
        raise GeocodeAPIException(message)
    r = json.loads(r.content)
    if r['status'] != 'OK':
        message = 'Received bad status {} from geocode api request: {}'.format(r['status'], url)
        logger.error(message)
        raise GeocodeAPIException(message)
    latitude = r['results'][0]['geometry']['location']['lat']
    longitude = r['results'][0]['geometry']['location']['lng']
    return latitude, longitude


def get_child_service_bodies(parents):
    ret = []
    children = parents
    while children:
        children = [c.id for c in ServiceBody.objects.filter(parent__in=children) if c.id not in ret]
        ret.extend(children)
    return ret


def get_parent_service_bodies(children):
    ret = []
    parents = children
    while parents:
        parents = [p.parent.pk for p in ServiceBody.objects.filter(pk__in=parents) if p.parent is not None and p.parent.pk not in ret]
        ret.extend(parents)
    return ret


def get_search_results(params):
    page_size = params.get('page_size')
    page_size = abs(int(page_size)) if page_size is not None else page_size
    page_num = params.get('page_num')
    page_num = abs(int(page_num)) if page_num is not None else page_num

    meeting_ids = params.getlist('meeting_ids[]', [])
    meeting_ids = [int(m) for m in meeting_ids]

    weekdays = params.get('weekdays')
    weekdays = params.getlist('weekdays[]', []) if weekdays is None else [weekdays]
    weekdays = [int(w) for w in weekdays]
    weekdays_include = [w for w in weekdays if w > 0]
    weekdays_exclude = [abs(w) for w in weekdays if w < 0]

    venue_types = params.get('venue_types')
    venue_types = params.getlist('venue_types[]', []) if venue_types is None else [venue_types]
    venue_types = [int(vt) for vt in venue_types]
    venue_types_include = [vt for vt in venue_types if vt > 0]
    venue_types_exclude = [vt for vt in venue_types if vt < 0]

    services = params.get('services')
    services = params.getlist('services[]', []) if services is None else [services]
    services = [int(s) for s in services]
    services_include = [s for s in services if s > 0]
    services_exclude = [abs(s) for s in services if s < 0]
    recursive = params.get('recursive', None) == '1'
    if recursive:
        services_include.extend(get_child_service_bodies(services_include))
        services_exclude.extend(get_child_service_bodies(services_exclude))

    formats = params.get('formats')
    formats = params.getlist('formats[]', []) if formats is None else [formats]
    formats = [int(f) for f in formats]
    formats_include = [f for f in formats if f > 0]
    formats_exclude = [abs(f) for f in formats if f < 0]
    formats_comparison_operator = 'AND' if params.get('formats_comparison_operator') != 'OR' else 'OR'

    root_server_ids = params.get('root_server_ids')
    root_server_ids = params.getlist('root_server_ids[]', []) if root_server_ids is None else [root_server_ids]
    root_server_ids = [int(rs) for rs in root_server_ids]
    root_server_ids_include = [rs for rs in root_server_ids if rs > 0]
    root_server_ids_exclude = [abs(rs) for rs in root_server_ids if rs < 0]

    meeting_key = params.get('meeting_key')
    meeting_key_value = params.get('meeting_key_value')

    data_field_keys = extract_specific_keys_param(params)

    starts_after = parse_time_params(params.get('StartsAfterH'), params.get('StartsAfterM'))
    starts_before = parse_time_params(params.get('StartsBeforeH'), params.get('StartsBeforeM'))
    ends_before = parse_time_params(params.get('EndsBeforeH'), params.get('EndsBeforeM'))
    min_duration = parse_timedelta_params(params.get('MinDurationH'), params.get('MinDurationM'))
    max_duration = parse_timedelta_params(params.get('MaxDurationH'), params.get('MaxDurationM'))

    long_val = params.get('long_val')
    lat_val = params.get('lat_val')
    geo_width = params.get('geo_width')
    geo_width_km = params.get('geo_width_km')
    sort_results_by_distance = params.get('sort_results_by_distance', None) == '1'

    search_string = params.get('SearchString')
    search_string_is_address = params.get('StringSearchIsAnAddress', None) == '1'
    search_string_radius = params.get('SearchStringRadius')
    search_string_all = params.get('SearchStringAll', None) == '1'
    search_string_exact = params.get('SearchStringExact', None) == '1'

    sort_keys = extract_specific_keys_param(params, 'sort_keys', distance_field_keys)
    if not sort_keys:
        # default sort order
        sort_keys = ['lang_enum', 'weekday_tinyint', 'start_time', 'id_bigint']

    has_required_filter = False

    meeting_qs = Meeting.objects.filter(deleted=False, published=True)
    if data_field_keys:
        select_related_fields = ['meetinginfo']
        if 'service_body_bigint' in data_field_keys:
            select_related_fields.append('service_body')
            meeting_qs = meeting_qs.select_related(*select_related_fields)
    else:
        meeting_qs = meeting_qs.select_related('meetinginfo', 'service_body', 'root_server')

    if meeting_ids:
        has_required_filter = True
        meeting_qs = meeting_qs.filter(pk__in=meeting_ids)
    if weekdays_include:
        meeting_qs = meeting_qs.filter(weekday__in=weekdays_include)
    if weekdays_exclude:
        meeting_qs = meeting_qs.exclude(weekday__in=weekdays_exclude)
    if venue_types_include:
        meeting_qs = meeting_qs.filter(venue_type__in=venue_types_include)
    if venue_types_exclude:
        meeting_qs = meeting_qs.exclude(venue_type__in=venue_types_exclude)
    if services_include:
        has_required_filter = True
        meeting_qs = meeting_qs.filter(service_body_id__in=services_include)
    if services_exclude:
        meeting_qs = meeting_qs.exclude(service_body_id__in=services_exclude)
    if formats_include:
        has_required_filter = True
        if formats_comparison_operator == 'AND':
            for id in formats_include:
                meeting_qs = meeting_qs.filter(models.Q(formats__id=id))
        else:
            condition = None
            for id in formats_include:
                if condition is None:
                    condition = models.Q(formats__id=id)
                else:
                    condition |= models.Q(formats__id=id)
            meeting_qs = meeting_qs.filter(condition)
    if formats_exclude:
        for id in formats_exclude:
            meeting_qs = meeting_qs.filter(~models.Q(formats__id=id))
    if root_server_ids_include:
        has_required_filter = True
        meeting_qs = meeting_qs.filter(root_server_id__in=root_server_ids_include)
    if root_server_ids_exclude:
        meeting_qs = meeting_qs.exclude(root_server_id__in=root_server_ids_exclude)
    if meeting_key and meeting_key_value:
        has_required_filter = True
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
    if search_string and not search_string_is_address:
        has_required_filter = True
        vector_fields = (
            'name',
            'meetinginfo__location_text',
            'meetinginfo__location_info',
            'meetinginfo__location_street',
            'meetinginfo__location_city_subsection',
            'meetinginfo__location_neighborhood',
            'meetinginfo__location_municipality',
            'meetinginfo__location_sub_province',
            'meetinginfo__location_province',
            'meetinginfo__location_postal_code_1',
            'meetinginfo__location_nation',
            'meetinginfo__comments',
        )
        if search_string_exact:
            meeting_qs = meeting_qs.annotate(fields=Concat(*vector_fields, output_field=models.TextField()))
            meeting_qs = meeting_qs.filter(fields__icontains=search_string)
        else:
            vector = SearchVector(*vector_fields)
            meeting_qs = meeting_qs.annotate(search=vector)
            if search_string_all:
                meeting_qs = meeting_qs.filter(search=search_string)
            else:
                meeting_ids = []
                query = None
                for word in search_string.replace(',', ' ').split():
                    if word.isdigit():
                        meeting_ids.append(int(word))
                        continue
                    elif len(word) < 3 or word.lower() == 'the':
                        continue
                    q = SearchQuery(word)
                    query = q if not query else query | q
                q = None
                if query:
                    q = models.Q(search=query)
                if meeting_ids:
                    if not q:
                        q = models.Q(id=meeting_ids.pop())
                    for meeting_id in meeting_ids:
                        q = q | models.Q(id=meeting_id)
                if q:
                    meeting_qs = meeting_qs.filter(q)
    is_geo = (long_val and lat_val and (geo_width or geo_width_km or set(data_field_keys).intersection(distance_field_keys))) or (search_string and search_string_is_address)
    if is_geo:
        # Get latitude and longitude values, either directly from the request
        # or from the an address
        has_required_filter = True
        try:
            get_nearest = False
            if search_string and search_string_is_address:
                get_nearest = 10
                if search_string_radius:
                    search_string_radius = int(search_string_radius)
                    if search_string_radius < 0:
                        get_nearest = abs(search_string_radius)
                latitude, longitude = address_to_coordinates(search_string)
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
                else:
                    get_nearest = sys.maxsize
            point = Point(x=longitude, y=latitude, srid=4326)
        except Exception as e:
            if isinstance(e, ValueError) or isinstance(e, GeocodeAPIException):
                meeting_qs = meeting_qs.filter(pk=-1)
            else:
                raise
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
    if data_field_keys:
        values = []
        for key in data_field_keys:
            model_field = meeting_field_map.get(key)[0]
            if key in distance_field_keys:
                continue
            elif isinstance(model_field, tuple):
                field_name = model_field[0].replace('.', '__')
                agg_name = model_field[1]
                meeting_qs = meeting_qs.annotate(**{agg_name: ArrayAgg(field_name)})
            elif not callable(model_field):
                model_field = model_field.replace('.', '__')
                values.append(model_field)
        meeting_qs = meeting_qs.only(*values)
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
    if page_size is not None and page_num is not None:
        has_required_filter = True
        offset = page_size * (page_num - 1)
        limit = offset + page_size
        meeting_qs = meeting_qs[offset:limit]
    if not has_required_filter:
        logger.error("GetSearchResults request did not have a required filter")
        return meeting_qs.none()
    # We can't do prefetch related because we use .iterator() to stream results from the db
    # return meeting_qs.prefetch_related('formats')
    return meeting_qs


def get_field_values(params):
    root_server_id = params.get('root_server_id')
    meeting_key = params.get('meeting_key')
    meeting_qs = Meeting.objects.filter(deleted=False, published=True)
    if root_server_id:
        meeting_qs = meeting_qs.filter(root_server_id=root_server_id)
    if meeting_key in field_keys:
        model_field = meeting_field_map.get(meeting_key)[0]
        if isinstance(model_field, tuple):
            # This means we have a m2m field. At the time of this writing, the only
            # m2m field we have is formats. In this case, we want to get the distinct
            # list of format_ids for all meetings, and then get all meetings that have
            # the same formats in the "ids" Array
            id_field = '__'.join(model_field[0].split('.')[0:-1]) + '__id'
            meeting_qs = meeting_qs.annotate(**{model_field[1]: ArrayAgg(id_field)})
            meeting_qs = meeting_qs.annotate(
                ids=Window(
                    expression=ArrayAgg('id'),
                    partition_by=[F(model_field[1])]
                )
            )
            meeting_qs = meeting_qs.values(model_field[1], 'ids')
            meeting_qs = meeting_qs.distinct()
        else:
            if model_field:
                model_field = model_field.replace('.', '__')
                meeting_qs = meeting_qs.values(model_field)
                meeting_qs = meeting_qs.annotate(ids=ArrayAgg('id'))
    return meeting_qs


def get_formats(params):
    root_server_id = params.get('root_server_id')
    root_server_ids = params.get('root_server_ids')
    root_server_ids = params.getlist('root_server_ids[]', []) if root_server_ids is None else [root_server_ids]
    if root_server_id:
        root_server_ids.append(root_server_id)
    root_server_ids = [int(rs) for rs in root_server_ids]
    root_server_ids_include = [rs for rs in root_server_ids if rs > 0]
    root_server_ids_exclude = [abs(rs) for rs in root_server_ids if rs < 0]

    key_strings = params.get('key_strings')
    key_strings = params.getlist('key_strings[]', []) if key_strings is None else [key_strings]

    language = params.get('lang_enum', default='en')
    format_qs = TranslatedFormat.objects.filter(language=language)
    format_qs = format_qs.select_related('format')
    if root_server_ids_include:
        format_qs = format_qs.filter(format__root_server_id__in=root_server_ids_include)
    if root_server_ids_exclude:
        format_qs = format_qs.exclude(format__root_server_id__in=root_server_ids_exclude)
    if key_strings:
        format_qs = format_qs.filter(key_string__in=key_strings)
    return format_qs


def get_service_bodies(params):
    root_server_id = params.get('root_server_id')
    root_server_ids = params.get('root_server_ids')
    root_server_ids = params.getlist('root_server_ids[]', []) if root_server_ids is None else [root_server_ids]
    if root_server_id:
        root_server_ids.append(root_server_id)
    root_server_ids = [int(rs) for rs in root_server_ids]
    root_server_ids_include = [rs for rs in root_server_ids if rs > 0]
    root_server_ids_exclude = [abs(rs) for rs in root_server_ids if rs < 0]

    services = params.get('services')
    services = params.getlist('services[]', []) if services is None else [services]
    services = [int(s) for s in services]
    services_include = [s for s in services if s > 0]
    services_exclude = [abs(s) for s in services if s < 0]
    recursive = params.get('recursive', None) == '1'
    if recursive:
        services_include.extend(get_child_service_bodies(services_include))
        services_exclude.extend(get_child_service_bodies(services_exclude))
    parents = params.get('parents', None) == '1'
    if parents:
        services_include.extend(get_parent_service_bodies(services_include))
        services_exclude.extend(get_parent_service_bodies(services_exclude))

    body_qs = ServiceBody.objects.all()
    if root_server_ids_include:
        body_qs = body_qs.filter(root_server_id__in=root_server_ids_include)
    if root_server_ids_exclude:
        body_qs = body_qs.exclude(root_server_id__in=root_server_ids_exclude)
    if services_include:
        body_qs = body_qs.filter(id__in=services_include)
    if services_exclude:
        body_qs = body_qs.exclude(id__in=services_exclude)
    # BMLT returns top-level parents as having parent_id 0
    body_qs = body_qs.annotate(
        calculated_parent_id=Case(
            When(parent=None, then=Value(0)),
            default='parent_id',
            output_field=models.BigIntegerField()
        )
    )
    return body_qs


valid_switcher_params = (
    'GetSearchResults',
    'GetFormats',
    'GetServiceBodies',
    'GetFieldKeys',
    'GetFieldValues',
    'GetServerInfo',
    'GetNAWSDump'
)


def semantic_query(request, format='json'):
    switcher = request.GET.get('switcher')
    if format not in ('csv', 'json', 'xml', 'jsonp', 'kml', 'poi'):
        return response.HttpResponseBadRequest()
    if not switcher:
        return response.HttpResponseBadRequest()
    if switcher not in valid_switcher_params:
        return response.HttpResponseBadRequest()
    if format in ('kml', 'poi') and switcher != 'GetSearchResults':
        return response.HttpResponseBadRequest()
    if format != 'csv' and switcher == 'GetNAWSDump':
        return response.HttpResponseBadRequest()
    if format == 'jsonp' and 'callback' not in request.GET:
        return response.HttpResponseBadRequest()

    params = request.GET.copy()

    ret = None
    if format == 'json':
        content_type = 'application/json'
    elif format == 'jsonp':
        content_type = 'text/javascript'
    elif format in ('csv', 'poi'):
        content_type = 'text/csv'
    elif format in ('xml', 'kml'):
        content_type = 'application/xml'

    language = params.get('lang_enum', default='en')

    if switcher == 'GetSearchResults':
        if format in ('kml', 'poi') and 'data_field_key' in params:
            # Invalid parameter for kml and poi, as they always returns the same fields.
            params.pop('data_field_key')
        meetings = get_search_results(params)
        set_thread_language(language)
        data_field_keys = extract_specific_keys_param(params)
        if format in ('json', 'jsonp', 'xml'):
            if 'get_used_formats' in params or 'get_formats_only' in params:
                formats = TranslatedFormat.objects.filter(language=language, format__id__in=meetings.values('formats'))
                formats = formats.select_related('format', 'format__root_server')
            if format in ('json', 'jsonp'):
                if 'get_used_formats' in params or 'get_formats_only' in params:
                    if 'get_formats_only' in params:
                        ret = models_to_json(formats, format_field_map, parent_keys='formats')
                    else:
                        ret = models_to_json(
                            (meetings, formats),
                            (meeting_field_map, format_field_map),
                            related_models_filter_function=(None, None),
                            parent_keys=('meetings', 'formats'),
                            return_attrs=(data_field_keys, None)
                        )
                else:
                    ret = models_to_json(
                        meetings,
                        meeting_field_map,
                        related_models_filter_function=None,
                        return_attrs=data_field_keys
                    )
            else:
                xmlns = '{}://{}'.format(request.scheme, request.get_host())
                if 'get_used_formats' in params or 'get_formats_only' in params:
                    if 'get_formats_only' in params:
                        ret = models_to_xml(formats, format_field_map, 'formats', xmlns=xmlns, schema_name='GetFormats')
                    else:
                        ret = models_to_xml(
                            meetings, meeting_field_map, 'meetings',
                            related_models_filter_function=None,
                            xmlns=xmlns,
                            schema_name=switcher,
                            sub_models=formats,
                            sub_models_field_map=format_field_map,
                            sub_models_element_name='formats'
                        )
                else:
                    ret = models_to_xml(
                        meetings, meeting_field_map, 'meetings',
                        related_models_filter_function=None,
                        xmlns=xmlns, schema_name=switcher
                    )
        elif format == 'kml':
            meetings = apply_kml_annotations(meetings)
            ret = models_to_xml(meetings, meeting_kml_field_map, 'kml.Document',
                                model_name='Placemark', show_sequence_index=False)
        elif format == 'poi':
            meetings = meetings.order_by('weekday')
            meetings = apply_kml_annotations(meetings)
            ret = models_to_csv(meetings, meeting_poi_field_map)
        elif format == 'csv':
            ret = models_to_csv(meetings, meeting_field_map, data_field_keys)
    else:
        xml_schema_name = None
        if switcher == 'GetNAWSDump':
            sb_id = params.get('sb_id', None)
            if not sb_id:
                return response.HttpResponseBadRequest()
            sb_ids = [sb for sb in get_child_service_bodies([sb_id])]
            qs = Meeting.objects.filter(deleted=False, published=True)
            qs = qs.filter(service_body_id__in=sb_ids, service_body__world_id__isnull=False)
            qs = qs.exclude(service_body__world_id='')
            qs = qs.select_related('meetinginfo', 'service_body', 'root_server')
            qs = qs.prefetch_related('formats', 'formats__translatedformats')
            qs_union = Meeting.objects.filter(Q(deleted=True) | Q(published=False))
            qs_union = qs_union.filter(service_body_id__in=sb_ids, service_body__world_id__isnull=False)
            qs_union = qs_union.exclude(service_body__world_id='')
            qs_union = qs_union.select_related('meetinginfo', 'service_body', 'root_server')
            qs_union = qs_union.prefetch_related('formats', 'formats__translatedformats')
            models = qs.union(qs_union, all=True)
            field_map = naws_dump_field_map
        elif switcher == 'GetFormats':
            models = get_formats(params)
            field_map = format_field_map
            xml_node_name = 'formats'
            xml_schema_name = switcher
        elif switcher == 'GetServiceBodies':
            models = get_service_bodies(params)
            field_map = service_bodies_field_map
            xml_node_name = 'serviceBodies'
        elif switcher == 'GetFieldKeys':
            models = [{'key': k, 'description': d} for k, d in field_keys_with_descriptions.items()]
            field_map = {'key': ('key',), 'description': ('description',)}
            xml_node_name = 'fields'
        elif switcher == 'GetFieldValues':
            meeting_key = params.get('meeting_key')
            if meeting_key in field_keys:
                models = get_field_values(params)
                field_map = {meeting_key: (meeting_field_map.get(meeting_key)[0],), 'ids': ('ids',)}
                xml_node_name = 'fields'
            else:
                return response.HttpResponseBadRequest()
        elif switcher == 'GetServerInfo':
            models = [{
                'version': '5.0.0',
                'versionInt': '5000000',
                'langs': 'en',
                'nativeLang': 'en',
                'centerLongitude': -118.563659,
                'centerLatitude': 34.235918,
                'centerZoom': 6,
                'available_keys': ','.join(field_keys),
                'changesPerMeeting': '0',
                'google_api_key': settings.GOOGLE_MAPS_API_KEY,
            }]
            field_map = server_info_field_map
            xml_node_name = 'serverInfo'

        if format in ('json', 'jsonp'):
            ret = models_to_json(models, field_map)
        elif format == 'csv':
            ret = models_to_csv(models, field_map)
        elif format == 'xml':
            xmlns = '{}://{}'.format(request.scheme, request.get_host())
            ret = models_to_xml(models, field_map, xml_node_name, xmlns=xmlns, schema_name=xml_schema_name)

    if format == 'jsonp':
        return JSONPStreamingHttpResponse(ret, content_type=content_type, callback=params.get('callback'))

    r = response.StreamingHttpResponse(ret, content_type=content_type)
    if format == 'poi':
        r['Content-Disposition'] = 'attachment; filename="SearchResultsPOI.csv"'
    elif format == 'kml':
        r['Content-Disposition'] = 'attachment; filename="SearchResults.kml"'
    elif format == 'csv' and switcher == 'GetNAWSDump':
        r['Content-Disposition'] = 'attachment; filename="BMLT.csv"'

    return r


def get_service_bodies_php(request):
    models = get_service_bodies(request.GET)
    ret = models_to_xml(models, service_bodies_field_map, 'serviceBodies')
    return response.HttpResponse(ret, content_type='application/xml')


def get_langs_php(request, format='json'):
    if format == 'jsonp' and 'callback' not in request.GET:
        return response.HttpResponseBadRequest()

    lang_to_name = {
        "en": "English",
        "de": "Deutsch",
        "dk": "Dansk",
        "es": "Español",
        "fa": "فارسی",
        "fr": "Français",
        "it": "Italiano",
        "pl": "Polskie",
        "pt": "Português",
        "sv": "Svenska"
    }

    languages = TranslatedFormat.objects.values_list('language', flat=True).distinct()
    if format in ('json', 'jsonp'):
        content_type = 'application/json'
        ret = {"languages": []}
        for language in languages:
            ret["languages"].append({
                "key": language,
                "name": lang_to_name.get(language, ''),
                "default": True if language == 'en' else False
            })
        ret = json.dumps(ret)
        if format == 'jsonp':
            ret = request.GET.get('callback') + '(' + ret + ')'
    else:
        content_type = 'application/xml'
        ret = "<languages>"
        for language in languages:
            ret += '\n  <language key="{}"{}>{}</language>'.format(
                language,
                ' default="1"' if language == 'en' else "",
                lang_to_name.get(language, '')
            )
        ret += "\n</languages>"

    return response.HttpResponse(ret, content_type=content_type)


def server_info_xml(request):
    ret = textwrap.dedent("""
    <bmltInfo>
        <serverVersion>
            <readableString>5.0.0</readableString>
        </serverVersion>
    </bmltInfo>
    """)
    return response.HttpResponse(ret, content_type='application/xml')


def xsd(request, schema_name):
    ret = render_to_string(
        schema_name + '.xsd',
        request=request,
        context={'url': '{}://{}'.format(request.scheme, request.get_host())}
    )
    return response.HttpResponse(ret, content_type='text/xml')


def ping(request):
    return response.HttpResponse("pong", content_type='text/plain')


def server_root(request):
    return response.HttpResponse("tomato", content_type='text/plain')
