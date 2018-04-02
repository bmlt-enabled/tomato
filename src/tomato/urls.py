from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.views import serve
from django.urls import path
from rest_framework import routers
import re
from .api import views, viewsets


router = routers.DefaultRouter()
router.register(r'rootservers', viewsets.RootServerViewSet)
router.register(r'servicebodies', viewsets.ServiceBodyViewSet)
router.register(r'formats', viewsets.FormatViewSet)
router.register(r'meetings', viewsets.MeetingViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    url('ping/$', views.ping, name='ping'),
    # semantic api
    url(r'main_server[/]+client_interface/xml/GetServiceBodies.php$', views.get_service_bodies_php, name='get-service-bodies-php'),
    url(r'main_server[/]+client_interface/(?P<format>json|xml|jsonp)/GetLangs.php$', views.get_langs_php, name='get-langs-php'),
    url(r'main_server[/]+client_interface/(?P<format>json|csv|xml|jsonp|kml)/', views.semantic_query, name='semantic-query'),
    url(r'main_server[/]+client_interface/serverInfo.xml$', views.server_info_xml, name='server-info-xml'),
    url(r'main_server[/]+client_interface/xsd/(?P<schema_name>GetSearchResults|GetFormats)\.php$', views.xsd, name='xsd'),
    # rest api
    url('^rest/v1/', include(router.urls)),
    # static
    url(r'^%s/(?P<path>.*)$' % re.escape(settings.STATIC_URL.strip('/')), serve, kwargs={'insecure': True}),
]
