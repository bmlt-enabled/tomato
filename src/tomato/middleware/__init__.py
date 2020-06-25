import logging
from django.conf import settings
from django.core.cache import cache
from ..api.models import RootServer

try:
    import uwsgi
except ImportError:
    UWSGI_ENABLED = False
else:
    UWSGI_ENABLED = True

logger = logging.getLogger('django')


class FormatsCacheInvalidatingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.CACHE_FORMATS and UWSGI_ENABLED:
            current_data_version = RootServer.objects.order_by('-last_successful_import')
            current_data_version = current_data_version.values_list('last_successful_import', flat=True)
            current_data_version = str(current_data_version[0])
            cache_data_version = uwsgi.cache_get('cache_data_version')
            if cache_data_version:
                cache_data_version = cache_data_version.decode('utf-8')
            if current_data_version != cache_data_version:
                logger.info("clearing cache, current_data_version: {}, cache_data_version: {}".format(
                    current_data_version, cache_data_version
                ))
                cache.clear()
                uwsgi.cache_update('cache_data_version', current_data_version)

        response = self.get_response(request)
        return response
