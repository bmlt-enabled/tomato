import json
import logging
import requests
import requests.exceptions
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections, transaction, DatabaseError
from django.utils import timezone
from urllib.parse import urljoin
from ...models import Format, ImportProblem, Meeting, RootServer, ServiceBody


logger = logging.getLogger('django')



class Command(BaseCommand):
    help = 'Updates the meetings database from root servers'

    def handle(self, *args, **options):
        logger.info('retrieving root servers')
        url = 'https://raw.githubusercontent.com/LittleGreenViper/BMLTTally/master/rootServerList.json'
        try:
            root_servers = json.loads(self.request(url))
            for root_server in root_servers:
                root_server['rootURL'] = root_server['rootURL'].strip()
                if not root_server['rootURL'].endswith('/'):
                    root_server['rootURL'] += '/'
        except Exception as e:
            logger.error('Error retrieving root server list: {}'.format(str(e)))
        else:
            for old in RootServer.objects.exclude(url__in=[r['rootURL'] for r in root_servers]):
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
            raise Exception('Unexpected status code from root server')
        return response.content

    def get_root_server_instance(self, root_server_json_object):
        root = RootServer.objects.get_or_create(url=root_server_json_object['rootURL'])[0]
        root.name = root_server_json_object['name']
        root.server_info = self.request(urljoin(root.url, 'client_interface/json/?switcher=GetServerInfo'))
        root.server_info = json.dumps(json.loads(root.server_info))
        return root

    def update_root_server_stats(self, root):
        root.num_regions = ServiceBody.objects.filter(root_server=root, type=ServiceBody.REGION).count()
        root.num_areas = ServiceBody.objects.filter(root_server=root).exclude(type=ServiceBody.REGION).count()
        root.num_meetings = Meeting.objects.filter(root_server=root).count()

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
        url = urljoin(root.url, 'client_interface/json/?switcher=GetFormats')
        formats = json.loads(self.request(url))
        Format.import_from_bmlt_objects(root, formats)

    def update_meetings(self, root):
        url = urljoin(root.url, 'client_interface/json/?switcher=GetSearchResults')
        meetings = json.loads(self.request(url))
        ignore_bodies = settings.IGNORE_SERVICE_BODIES.get(root.url)
        if ignore_bodies:
            meetings = [m for m in meetings if int(m['service_body_bigint']) not in ignore_bodies]
        Meeting.import_from_bmlt_objects(root, meetings)
