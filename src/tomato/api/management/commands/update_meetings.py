import datetime
import json
import pytz
import requests
import requests.exceptions
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from urllib.parse import urljoin
from ...models import Format, Meeting, RootServer, ServiceBody


class Command(BaseCommand):
    help = 'Updates the meetings database from root servers'

    def handle(self, *args, **options):
        for old in RootServer.objects.exclude(url__in=settings.ROOT_SERVERS):
            try:
                old.delete()
            except:
                # TODO This probably means a root server was removed from the list, but we can't
                # delete it because it has objects referencing it that depend on it. We should log
                # something so that we can decide what to do about it. Maybe we want to keep the historical
                # data, maybe we don't.
                pass

        for url in settings.ROOT_SERVERS:
            if not url.endswith('/'):
                url += '/'
            root = RootServer.objects.get_or_create(url=url)[0]
            try:
                with transaction.atomic():
                    self.update_service_bodies(root)
                    self.update_formats(root)
                    self.update_meetings(root)
            except Exception as e:
                # TODO Update something on the root_server indicating last successful sync and last tried sync
                raise

    def update_service_bodies(self, root):
        url = urljoin(root.url, 'client_interface/json/?switcher=GetServiceBodies')
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception('Unexpected status code from root server')
        service_bodies = json.loads(response.content)

        # Get them inserted/updated
        for new_body in service_bodies:
            source_id = new_body.get('id')
            if not source_id:
                raise Exception('Invalid source id')
            body = ServiceBody.objects.get_or_create(root_server=root, source_id=source_id)[0]
            body.name = new_body.get('name')
            body.description = new_body.get('description')
            body.type = new_body.get('type')
            body.url = new_body.get('url')
            body.world_id = new_body.get('world_id')
            body.parent = None
            body.save()

        # Update their parents
        for new_body in service_bodies:
            source_id = new_body.get('id')
            parent_source_id = new_body['parent_id']
            if not parent_source_id or parent_source_id == '0':
                continue
            body = ServiceBody.objects.get(root_server=root, source_id=source_id)
            body.parent = ServiceBody.objects.get(root_server=root, source_id=parent_source_id)
            body.save()

    def update_formats(self, root):
        url = urljoin(root.url, 'client_interface/json/?switcher=GetFormats')
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception('Unexpected status code from root server')
        formats = json.loads(response.content)

        for new_format in formats:
            source_id = new_format.get('id')
            if not source_id:
                raise Exception('Invalid source id')
            format = Format.objects.get_or_create(root_server=root, source_id=source_id)[0]
            format.key_string = new_format.get('key_string')
            format.name = new_format.get('name_string')
            format.description = new_format.get('description_string')
            format.language = new_format.get('lang')
            format.world_id = new_format.get('world_id')
            format.save()

    def update_meetings(self, root):
        url = urljoin(root.url, 'client_interface/json/?switcher=GetSearchResults')
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception('Unexpected status code from root server')
        meetings = json.loads(response.content)
        meeting_ids = [int(m['id_bigint']) for m in meetings]
        Meeting.objects.filter(root_server=root).exclude(source_id__in=meeting_ids).delete()
        for new_meeting in meetings:
            source_id = new_meeting.get('id_bigint')
            service_body_id = new_meeting.get('service_body_bigint')
            try:
                meeting = Meeting.objects.get(root_server=root, source_id=source_id)
            except Meeting.DoesNotExist:
                meeting = Meeting(root_server=root, source_id=source_id)

            try:
                service_body = ServiceBody.objects.get(root_server=root, source_id=service_body_id)
            except ServiceBody.DoesNotExist:
                # TODO log something
                continue
            meeting.name = new_meeting.get('meeting_name')
            meeting.service_body = service_body
            meeting.weekday = int(new_meeting.get('weekday_tinyint'))
            start_time = new_meeting.get('start_time')
            meeting.start_time = None if not start_time else datetime.time(*[int(t) for t in start_time.split(':')]).replace(tzinfo=datetime.timezone.utc)
            duration = new_meeting.get('duration_time')
            if duration and ':' not in duration:
                # So this is irregular, and we really should be logging something for each of those
                # so that we can a) investigate and b) figure out if we can get the data fixed at the source
                # either through user education or bug fixing of the BMLT

                # We are just assuming this is in minutes
                duration = int(duration)
                if duration < 60:
                    duration = '00:' + str(duration)
                else:
                    hours = int(duration / 60)
                    minutes = duration % 60
                    duration = str(hours) + ':' + str(minutes)


            meeting.duration = None if not duration else datetime.time(*[int(t) for t in duration.split(':')]).replace(tzinfo=datetime.timezone.utc)
            meeting.language = new_meeting.get('lang_enum')
            meeting.latitude = new_meeting.get('latitude')
            meeting.longitude = new_meeting.get('longitude')
            meeting.published = new_meeting.get('published') == '1'
            meeting.save()

            # Meeting must be saved before a m2m can be set
            formats = new_meeting.get('formats')
            if formats:
                formats = Format.objects.filter(root_server=root, key_string__in=formats.split(','))
                meeting.formats.set(formats)
            else:
                meeting.formats.clear()
            pass

