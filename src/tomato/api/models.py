import datetime
import decimal
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point


class ImportException(Exception):
    def __init__(self, message, bmlt_object):
        self.bmlt_object = bmlt_object
        super().__init__(message)


def set_if_changed(obj, attr_name, attr_value):
    if hasattr(obj, attr_name):
        current_value = getattr(obj, attr_name)
    else:
        current_value = None
    if attr_value != current_value:
        setattr(obj, attr_name, attr_value)
        return True
    return False


def get_key(d, key):
    try:
        return d[key]
    except KeyError:
        raise ImportException('Key {} does not exist'.format(key), d)


def get_required_str(d, key):
    value = get_key(d, key)
    if not value:
        raise ImportException('Missing required key {}'.format(key), d)
    return value


def get_decimal(d, key):
    value = get_key(d, key)
    try:
        return decimal.Decimal(value)
    except decimal.InvalidOperation:
        raise ImportException('Invalid {}'.format(key), d)


def get_int(d, key, valid_choices=None):
    try:
        value = int(get_key(d, key))
    except ValueError:
        raise ImportException('Malformed {}'.format(key), d)
    if valid_choices and value not in valid_choices:
        raise ImportException('Invalid {}'.format(key), d)
    return value


def get_time(d, key):
    try:
        value = get_key(d, key)
        if ':' not in value:
            # assume we're dealing with minutes
            value = int(value)
            if value < 60:
                value = '00:' + str(value)
            else:
                hours = int(value / 60)
                minutes = value % 60
                value = str(hours) + ':' + str(minutes)
        value = [int(t) for t in value.split(':')]
        value = datetime.time(*value)
        value.replace(tzinfo=datetime.timezone.utc)
        return value
    except ValueError:
        raise ImportException('Malformed {}'.format(key), d)
    except TypeError:
        raise ImportException('Malformed {}'.format(key), d)
    except ImportException:
        raise
    except Exception:
        raise ImportException('Unknown problem with {}'.format(key), d)


def get_timedelta(d, key):
    try:
        value = get_key(d, key)
        if ':' not in value:
            # assume we're dealing with minutes
            value = int(value)
            if value < 60:
                hours = 0
                minutes = str(value)
            else:
                hours = int(value / 60)
                minutes = value % 60
            return datetime.timedelta(hours=hours, minutes=minutes)
        else:
            value = [int(t) for t in value.split(':')]
            return datetime.timedelta(hours=value[0], minutes=value[1])
    except ValueError:
        raise ImportException('Malformed {}'.format(key), d)
    except TypeError:
        raise ImportException('Malformed {}'.format(key), d)
    except ImportException:
        raise
    except Exception:
        raise ImportException('Unknown problem with {}'.format(key), d)


class RootServer(models.Model):
    id = models.BigAutoField(primary_key=True)
    url = models.URLField()

    def __str__(self):
        return '({}:{})'.format(self.id, self.url)


class ImportProblem(models.Model):
    id = models.BigAutoField(primary_key=True)
    root_server = models.ForeignKey(RootServer, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now=True)
    data = models.TextField()

    def __str__(self):
        return '({}:{}:{})'.format(self.id, self.root_server if self.root_server else '', self.message)


class ServiceBody(models.Model):
    AREA = 'AS'
    METRO = 'MA'
    REGION = 'RS'
    SERVICE_BODY_TYPE_CHOICES = (
        (AREA, 'Area'),
        (METRO, 'Metro'),
        (REGION, 'Region'),
    )
    id = models.BigAutoField(primary_key=True)
    source_id = models.BigIntegerField()
    root_server = models.ForeignKey(RootServer, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=2, choices=SERVICE_BODY_TYPE_CHOICES)
    description = models.TextField(null=True)
    url = models.URLField(null=True)
    world_id = models.CharField(max_length=255, null=True)

    @staticmethod
    def import_from_bmlt_objects(root_server, bmlt_bodies):
        for bmlt_body in bmlt_bodies:
            try:
                bmlt_body = ServiceBody.validate_bmlt_object(root_server, bmlt_body)
            except ImportException as e:
                ImportProblem.objects.create(
                    root_server=root_server,
                    message=str(e),
                    data=str(e.bmlt_object)
                )
                continue

            body = ServiceBody.objects.get_or_create(root_server=root_server, source_id=bmlt_body['source_id'])[0]
            dirty = False
            field_names = ('name', 'type', 'description', 'url', 'world_id')
            changed_fields = []
            for field_name in field_names:
                if set_if_changed(body, field_name, bmlt_body[field_name]):
                    changed_fields.append(field_name)
                    dirty = True

            if dirty:
                body.save()

        for bmlt_body in bmlt_bodies:
            try:
                bmlt_body = ServiceBody.validate_bmlt_object(root_server, bmlt_body)
            except ImportException:
                continue
            source_id = bmlt_body.get('source_id')
            parent_source_id = bmlt_body.get('parent_id')
            body = ServiceBody.objects.get(root_server=root_server, source_id=source_id)
            if not parent_source_id:
                body.parent = None
            else:
                body.parent = ServiceBody.objects.get(root_server=root_server, source_id=parent_source_id)
            body.save()

    @staticmethod
    def validate_bmlt_object(root_server, bmlt):
        return {
            'source_id': get_int(bmlt, 'id'),
            'parent_id': get_int(bmlt, 'parent_id'),
            'name': get_required_str(bmlt, 'name'),
            'type': get_required_str(bmlt, 'type'),
            'description': bmlt.get('description', None),
            'url': bmlt.get('url', None),
            'world_id': bmlt.get('world_id', None),
        }

    def __str__(self):
        return '({}:{})'.format(self.id, self.name)


class Format(models.Model):
    id = models.BigAutoField(primary_key=True)
    source_id = models.BigIntegerField()
    root_server = models.ForeignKey(RootServer, on_delete=models.CASCADE)
    key_string = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True)
    language = models.CharField(max_length=7, default='en')
    world_id = models.CharField(max_length=255, null=True)

    @staticmethod
    def import_from_bmlt_objects(root_server, bmlt_formats):
        for bmlt_format in bmlt_formats:
            try:
                bmlt_format = Format.validate_bmlt_object(root_server, bmlt_format)
            except ImportException as e:
                ImportProblem.objects.create(
                    root_server=root_server,
                    message=str(e),
                    data=str(e.bmlt_object)
                )
                continue

            format = Format.objects.get_or_create(root_server=root_server, source_id=bmlt_format['source_id'])[0]
            dirty = False
            field_names = ('key_string', 'name', 'description', 'language', 'world_id')
            changed_fields = []
            for field_name in field_names:
                if set_if_changed(format, field_name, bmlt_format[field_name]):
                    changed_fields.append(field_name)
                    dirty = True

            if dirty:
                format.save()

    @staticmethod
    def validate_bmlt_object(root_server, bmlt):
        return {
            'source_id': get_int(bmlt, 'id'),
            'key_string': get_required_str(bmlt, 'key_string'),
            'name': get_required_str(bmlt, 'name_string'),
            'description': bmlt.get('description_string', None),
            'language': bmlt.get('lang'),
            'world_id': bmlt.get('world_id', None),
        }

    def __str__(self):
        return '({}:{}:{}:{})'.format(self.id, self.root_server, self.key_string, self.name)


class Meeting(models.Model):
    SUNDAY = 1
    MONDAY = 2
    TUESDAY = 3
    WEDNESDAY = 4
    THURSDAY = 5
    FRIDAY = 6
    SATURDAY = 7
    WEEKDAY_CHOICES = (
        (SUNDAY, 'Sunday'),
        (MONDAY, 'Monday'),
        (TUESDAY, 'Tuesday'),
        (WEDNESDAY, 'Wednesday'),
        (THURSDAY, 'Thursday'),
        (FRIDAY, 'Friday'),
        (SATURDAY, 'Saturday'),
    )
    VALID_WEEKDAY_INTS = [day[0] for day in WEEKDAY_CHOICES]
    id = models.BigAutoField(primary_key=True)
    source_id = models.BigIntegerField()
    root_server = models.ForeignKey(RootServer, on_delete=models.CASCADE)
    service_body = models.ForeignKey(ServiceBody, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    weekday = models.SmallIntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField(null=True)
    duration = models.DurationField(null=True)
    formats = models.ManyToManyField(Format)
    language = models.CharField(max_length=7, null=True)
    latitude = models.DecimalField(max_digits=15, decimal_places=12)
    longitude = models.DecimalField(max_digits=15, decimal_places=12)
    point = models.PointField(null=True, geography=True)
    published = models.BooleanField(default=False)

    @staticmethod
    def import_from_bmlt_objects(root_server, bmlt_meetings):
        for bmlt_meeting in bmlt_meetings:
            try:
                bmlt_meeting = Meeting.validate_bmlt_object(root_server, bmlt_meeting)
            except ImportException as e:
                ImportProblem.objects.create(
                    root_server=root_server,
                    message=str(e),
                    data=str(e.bmlt_object)
                )
                continue

            try:
                qs = Meeting.objects.prefetch_related('meetinginfo', 'service_body', 'formats')
                meeting = qs.get(root_server=root_server, source_id=bmlt_meeting.get('source_id'))
            except Meeting.DoesNotExist:
                meeting = Meeting(root_server=root_server, source_id=bmlt_meeting.get('source_id'))

            dirty = False
            field_names = ('service_body', 'name', 'weekday', 'start_time',
                           'duration', 'language', 'latitude', 'longitude',
                           'published')
            changed_fields = []
            for field_name in field_names:
                if set_if_changed(meeting, field_name, bmlt_meeting[field_name]):
                    changed_fields.append(field_name)
                    dirty = True

            if meeting.longitude and meeting.latitude:
                point = Point(float(meeting.longitude), float(meeting.latitude))
                if meeting.point != point:
                    meeting.point = point
                    dirty = True

            if dirty:
                meeting.save()

            try:
                meeting.meetinginfo
            except MeetingInfo.DoesNotExist:
                meeting.meetinginfo = MeetingInfo.objects.create(meeting=meeting)
                meeting.save()

            dirty = False
            for field_name in bmlt_meeting['meetinginfo'].keys():
                if set_if_changed(meeting.meetinginfo, field_name, bmlt_meeting['meetinginfo'][field_name]):
                    changed_fields.append(field_name)
                    dirty = True

            if dirty:
                meeting.meetinginfo.save()

            if bmlt_meeting['formats']:
                if meeting.formats != bmlt_meeting['formats']:
                    meeting.formats.set(bmlt_meeting['formats'])
            elif meeting.formats.exists():
                meeting.formats.clear()

    @staticmethod
    def validate_bmlt_object(root_server, bmlt_meeting):
        try:
            formats = bmlt_meeting.get('formats').split(',')
            return {
                'source_id': get_int(bmlt_meeting, 'id_bigint'),
                'service_body': ServiceBody.objects.get(root_server=root_server,
                                                        source_id=get_int(bmlt_meeting, 'service_body_bigint')),
                'name': get_required_str(bmlt_meeting, 'meeting_name'),
                'weekday': get_int(bmlt_meeting, 'weekday_tinyint', valid_choices=Meeting.VALID_WEEKDAY_INTS),
                'start_time': get_time(bmlt_meeting, 'start_time'),
                'duration': get_timedelta(bmlt_meeting, 'duration_time'),
                'language': bmlt_meeting.get('lang_enum', 'en'),
                'latitude': get_decimal(bmlt_meeting, 'latitude'),
                'longitude': get_decimal(bmlt_meeting, 'longitude'),
                'published': bmlt_meeting.get('published', '0') == '1',
                'formats': Format.objects.filter(root_server=root_server, key_string__in=formats),
                'meetinginfo': {
                    'email': bmlt_meeting.get('email_contact', None),
                    'contact_name_1': bmlt_meeting.get('contact_name_1', None),
                    'contact_name_2': bmlt_meeting.get('contact_name_2', None),
                    'contact_phone_1': bmlt_meeting.get('contact_phone_1', None),
                    'contact_phone_2': bmlt_meeting.get('contact_phone_2', None),
                    'location_text': bmlt_meeting.get('location_text', None),
                    'location_info': bmlt_meeting.get('location_info', None),
                    'location_street': bmlt_meeting.get('location_street', None),
                    'location_city_subsection': bmlt_meeting.get('location_city_subsection', None),
                    'location_neighborhood': bmlt_meeting.get('location_neighborhood', None),
                    'location_municipality': bmlt_meeting.get('location_municipality', None),
                    'location_sub_province': bmlt_meeting.get('location_sub_province', None),
                    'location_province': bmlt_meeting.get('location_province', None),
                    'location_postal_code_1': bmlt_meeting.get('location_postal_code_1', None),
                    'location_nation': bmlt_meeting.get('location_nation', None),
                    'train_lines': bmlt_meeting.get('train_lines', None),
                    'bus_lines': bmlt_meeting.get('bus_lines', None),
                    'world_id': bmlt_meeting.get('worldid_mixed', None),
                    'comments': bmlt_meeting.get('comments', None),
                }
            }
        except ServiceBody.DoesNotExist:
            raise ImportException('Invalid service_body', bmlt_meeting)

    def __str__(self):
        return '{} | {} | {} | {}'.format(self.id, self.root_server, self.service_body, self.name)


class MeetingInfo(models.Model):
    id = models.BigAutoField(primary_key=True)
    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE)
    email = models.EmailField(null=True)
    contact_name_1 = models.CharField(max_length=255, null=True)
    contact_name_2 = models.CharField(max_length=255, null=True)
    contact_email_1 = models.EmailField(null=True)
    contact_email_2 = models.EmailField(null=True)
    contact_phone_1 = models.CharField(max_length=255, null=True)
    contact_phone_2 = models.CharField(max_length=255, null=True)
    location_text = models.CharField(max_length=255, null=True)
    location_info = models.CharField(max_length=255, null=True)
    location_street = models.CharField(max_length=255, null=True)
    location_city_subsection = models.CharField(max_length=255, null=True)
    location_neighborhood = models.CharField(max_length=255, null=True)
    location_municipality = models.CharField(max_length=255, null=True)
    location_sub_province = models.CharField(max_length=255, null=True)
    location_province = models.CharField(max_length=255, null=True)
    location_postal_code_1 = models.CharField(max_length=255, null=True)
    location_nation = models.CharField(max_length=255, null=True)
    train_lines = models.CharField(max_length=255, null=True)
    bus_lines = models.CharField(max_length=255, null=True)
    world_id = models.CharField(max_length=255, null=True)
    comments = models.CharField(max_length=255, null=True)
