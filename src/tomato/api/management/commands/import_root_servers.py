import json
import logging
import requests
import requests.exceptions
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.management.base import BaseCommand
from django.db import connections, transaction, DatabaseError
from django.db.models import Count, Q, F, Sum
from django.utils import timezone
from urllib.parse import urljoin
from ...models import (Format, ImportProblem, Meeting, RootServer, ServiceBody,
                       get_int, get_required_str, get_decimal, ImportException)


logger = logging.getLogger('django')


def get_top_service_bodies_with_world_ids(root, parent=None):
    ret = []
    for sb in ServiceBody.objects.filter(root_server=root, parent=parent):
        if sb.world_id:
            ret.append(sb)
        else:
            ret.extend(get_top_service_bodies_with_world_ids(root, sb))
    return ret


def naws_meeting_to_bmlt_meeting(root, meeting):
    def get_weekday(m):
        day = get_required_str(m, 'Day')
        for weekday_int, weekday_name in Meeting.WEEKDAY_CHOICES:
            if weekday_name == day:
                return weekday_int
        raise ImportException('Invalid NAWS Day', m)

    def get_time(m):
        time = get_required_str(m, 'Time')
        if len(time) < 3:
            raise ImportException('Malformed NAWS Time {}'.format(time), m)
        minutes = time[-2:]
        hours = time[0:1 if len(time) == 3 else 2]
        return hours + ':' + minutes

    def get_formats(m):
        world_ids = []
        if m.get('Closed', 'CLOSED').strip() == 'CLOSED':
            world_ids.append('CLOSED')
        else:
            world_ids.append('OPEN')
        if m.get('WheelChr', 'FALSE').strip() == 'TRUE':
            world_ids.append('WCHR')
        for i in range(1, 6):
            world_id = m.get('Format{}'.format(i), '')
            if world_id:
                world_ids.append(world_id)
        qs = Format.objects.filter(root_server=root, world_id__in=world_ids)
        formats = [f for f in qs.values_list('key_string', flat=True).distinct()]
        return ','.join(formats)

    try:
        return {
            'id_bigint': get_int(meeting, 'bmlt_id'),
            'service_body_bigint': ServiceBody.objects.get(root_server=root,
                                                           world_id=get_required_str(meeting, 'AreaRegion')).source_id,
            'meeting_name': get_required_str(meeting, 'CommitteeName'),
            'weekday_tinyint': get_weekday(meeting),
            'start_time': get_time(meeting),
            'duration_time': '1:00',
            'lang_enum': 'en',
            'latitude': get_decimal(meeting, 'Latitude'),
            'longitude': get_decimal(meeting, 'Longitude'),
            'published': '1' if meeting.get('unpublished', '0') == '0' else '0',
            'formats': get_formats(meeting),
            'email_contact': None,
            'location_text': meeting.get('Place', None),
            'location_info': meeting.get('Directions', None),
            'location_street': meeting.get('Address', None),
            'location_neighborhood': meeting.get('LocBorough', None),
            'location_province': meeting.get('State', None),
            'location_postal_code_1': meeting.get('Zip', None),
            'location_nation': meeting.get('Country', None),
            'location_city_subsection': meeting.get('City', None),
            'worldid_mixed': meeting.get('Committee', None),
            'deleted': meeting.get('Delete', '').strip() == 'D'
        }
    except MultipleObjectsReturned:
        raise ImportException('Multiple service bodies with the world id exist', meeting)


class Command(BaseCommand):
    help = 'Updates the meetings database from root servers'

    def handle(self, *args, **options):
        url = 'https://raw.githubusercontent.com/bmlt-enabled/tomato/master/rootServerList.json'
        logger.info('retrieving root servers from {}'.format(url))
        try:
            root_servers = json.loads(self.request(url))
            for root_server in root_servers:
                root_server['rootURL'] = root_server['rootURL'].strip()
                if not root_server['rootURL'].endswith('/'):
                    root_server['rootURL'] += '/'
            root_servers = [root_server for root_server in root_servers if root_server['rootURL'] not in settings.IGNORE_ROOT_SERVERS]
        except Exception as e:
            logger.error('Error retrieving root server list: {}'.format(str(e)))
        else:
            for old in RootServer.objects.exclude(source_id__in=[int(r['id']) for r in root_servers]):
                try:
                    logger.info('Deleting old root server {}'.format(old.url))
                    old.delete()
                except Exception as e:
                    logger.error('Error deleting old root server {}'.format(str(e)))

            for root_server in root_servers:
                logger.info('importing root server {}'.format(root_server['rootURL']))
                try:
                    root = self.get_root_server_instance(root_server)
                    ImportProblem.objects.filter(root_server=root).delete()
                    with transaction.atomic():
                        logger.info('importing service bodies')
                        self.update_service_bodies(root)
                        logger.info('importing formats')
                        self.update_formats(root)
                        logger.info('importing meetings')
                        self.update_meetings(root)
                        logger.info('updating service body stats')
                        self.update_service_body_stats(root)
                        logger.info('updating root server stats')
                        self.update_root_server_stats(root)
                        root.last_successful_import = timezone.now()
                        root.save()
                except DatabaseError:
                    logger.exception('Encountered DatabaseError, closing database connection')
                    connections.close_all()
                except Exception as e:
                    logger.error('Error updating root server: {}'.format(str(e)))
            logger.info('done')

    def request(self, url):
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0 +tomato'}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception('Unexpected status code {} from root server'.format(response.status_code))
        return response.content

    def get_root_server_instance(self, root_server_json_object):
        root = RootServer.objects.get_or_create(source_id=int(root_server_json_object['id']))[0]
        root.name = root_server_json_object['name']
        root.url = root_server_json_object['rootURL']
        root.server_info = self.request(urljoin(root.url, 'client_interface/json/?switcher=GetServerInfo'))
        root.server_info = json.dumps(json.loads(root.server_info))
        root.save()
        return root

    def update_root_server_stats(self, root):
        root.num_zones = ServiceBody.objects.filter(root_server=root, type=ServiceBody.ZONE).count()
        root.num_regions = ServiceBody.objects.filter(root_server=root, type=ServiceBody.REGION).count()
        root.num_areas = ServiceBody.objects.filter(root_server=root).exclude(type=ServiceBody.REGION).count()
        root.num_meetings = Meeting.objects.filter(deleted=False, published=True, root_server=root).count()
        root.num_groups = ServiceBody.objects.filter(root_server=root, parent=None).aggregate(Sum('num_groups'))['num_groups__sum']

    def update_service_bodies(self, root):
        url = urljoin(root.url, 'client_interface/json/?switcher=GetServiceBodies')
        service_bodies = json.loads(self.request(url))
        ignore_bodies = settings.IGNORE_SERVICE_BODIES.get(root.url)
        if ignore_bodies:
            prev_len = len(service_bodies)
            service_bodies = [sb for sb in service_bodies if int(sb['id']) not in ignore_bodies]
            logger.info('ignored {} service bodies'.format(prev_len - len(service_bodies)))
        ServiceBody.import_from_bmlt_objects(root, service_bodies)

    def update_formats(self, root):
        formats = {}
        for language in json.loads(root.server_info)[0]['langs'].split(','):
            url = urljoin(root.url, 'client_interface/json/?switcher=GetFormats&lang_enum={}'.format(language))
            for fmt in json.loads(self.request(url)):
                if fmt['id'] not in formats:
                    formats[fmt['id']] = {}
                formats[fmt['id']][language] = fmt
        Format.import_from_bmlt_objects(root, formats)

    def update_meetings(self, root):
        url = urljoin(root.url, 'client_interface/json/?switcher=GetSearchResults')
        meetings = json.loads(self.request(url))
        ignore_bodies = settings.IGNORE_SERVICE_BODIES.get(root.url)
        if ignore_bodies:
            meetings = [m for m in meetings if int(m['service_body_bigint']) not in ignore_bodies]
        #meeting_ids = set([m['id_bigint'] for m in meetings])
        #for sb in get_top_service_bodies_with_world_ids(root):
        #    logger.info('...pulling naws dump for {}'.format(str(sb)))
        #    url = urljoin(root.url, 'client_interface/csv/?switcher=GetNAWSDump&sb_id={}'.format(sb.source_id))
        #    with io.StringIO(self.request(url).decode()) as s:
        #        for row in csv.DictReader(s):
        #            published = row.get('unpublished', '0').strip() != '1'
        #            deleted = row.get('Delete', '').strip() == 'D'
        #            sb_qs = ServiceBody.objects.filter(root_server=root, world_id=row['AreaRegion'])
        #            if row['bmlt_id'] not in meeting_ids and (not published or deleted) and sb_qs.exists():
        #                try:
        #                    meetings.append(naws_meeting_to_bmlt_meeting(root, row))
        #                    meeting_ids.add(row['bmlt_id'])
        #                except ImportException as e:
        #                    logger.warning('Error parsing naws dump meeting: {}'.format(str(e)))
        #                    ImportProblem.objects.create(root_server=root, message=str(e), data=str(e.bmlt_object))
        #                    continue
        Meeting.import_from_bmlt_objects(root, meetings)

    def update_service_body_stats(self, root):
        service_bodies = ServiceBody.objects.filter(root_server=root)
        service_bodies = service_bodies.annotate(count_meetings=Count('meeting__pk'))
        service_bodies = service_bodies.annotate(
            count_groups_world_ids=Count(
                'meeting__meetinginfo__world_id',
                distinct=True,
                filter=~Q(meeting__meetinginfo__world_id=None) & ~Q(meeting__meetinginfo__world_id='')
            )
        )
        service_bodies = service_bodies.annotate(
            count_groups_no_world_ids=Count(
                'meeting__name',
                distinct=True,
                filter=Q(meeting__meetinginfo__world_id=None) | Q(meeting__meetinginfo__world_id='')
            )
        )
        service_bodies = service_bodies.annotate(count_groups=F('count_groups_world_ids') + F('count_groups_no_world_ids'))
        service_bodies = list(service_bodies)
        parent_to_children = {service_body.pk: [sb for sb in service_bodies if sb.parent == service_body] for service_body in service_bodies}

        def get_all_children(service_body, children=None):
            if children is None:
                children = []
            for child in parent_to_children[service_body.pk]:
                if child not in children:
                    children.append(child)
                get_all_children(child, children)
            return children

        for service_body in service_bodies:
            children = get_all_children(service_body)
            service_body.num_meetings = sum([sb.count_meetings for sb in children]) + service_body.count_meetings
            service_body.num_groups = sum([sb.count_groups for sb in children]) + service_body.count_groups
            service_body.save()
