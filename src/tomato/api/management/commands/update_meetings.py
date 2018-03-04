import json
import requests
import requests.exceptions
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from urllib.parse import urljoin
from ...models import Format, ImportProblem, Meeting, RootServer, ServiceBody


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
            ImportProblem.objects.filter(root_server=root).delete()
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
        ServiceBody.import_from_bmlt_objects(root, service_bodies)

    def update_formats(self, root):
        url = urljoin(root.url, 'client_interface/json/?switcher=GetFormats')
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception('Unexpected status code from root server')
        formats = json.loads(response.content)
        Format.import_from_bmlt_objects(root, formats)

    def update_meetings(self, root):
        url = urljoin(root.url, 'client_interface/json/?switcher=GetSearchResults')
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception('Unexpected status code from root server')
        meetings = json.loads(response.content)

        # Delete meetings that no longer exist
        meeting_ids = [int(m['id_bigint']) for m in meetings]
        Meeting.objects.filter(root_server=root).exclude(source_id__in=meeting_ids).delete()

        # Import the rest
        Meeting.import_from_bmlt_objects(root, meetings)
