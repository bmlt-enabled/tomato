from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.contrib.staticfiles.views import serve
from django.urls import path
import re
from .api import views

urlpatterns = [
    path('admin/', admin.site.urls),

    url(r'_/sandwich/client_interface/xml/GetServiceBodies.php$',
        views.get_service_bodies_php,
        name='get-service-bodies-php-sandwich'),
    url(r'main_server[/]+client_interface/xml/GetServiceBodies.php$',
        views.get_service_bodies_php,
        name='get-service-bodies-php'),

    url(r'_/sandwich/client_interface/(?P<format>json|xml)/GetLangs.php$',
        views.get_langs_php,
        name='get-langs-php-sandwich'),
    url(r'main_server[/]+client_interface/(?P<format>json|xml)/GetLangs.php$',
        views.get_langs_php,
        name='get-langs-php'),

    url(r'_/sandwich/client_interface/(?P<format>json|csv|xml)/',
        views.semantic_query,
        name='semantic-query-sandwich'),
    url(r'main_server[/]+client_interface/(?P<format>json|csv|xml)/',
        views.semantic_query,
        name='semantic-query'),

    url(r'_/sandwich/client_interface/serverInfo.xml$',
        views.server_info_xml,
        name='server-info-xml-sandwich'),
    url(r'main_server[/]+client_interface/serverInfo.xml$',
        views.server_info_xml,
        name='server-info-xml'),

    url(r'^%s/(?P<path>.*)$' % re.escape(settings.STATIC_URL.strip('/')), serve, kwargs={'insecure': True}),
]
