from django.db import models


class RootServer(models.Model):
    id = models.BigAutoField(primary_key=True)
    url = models.URLField()


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
    root_server = models.ForeignKey(RootServer, on_delete=models.PROTECT)
    parent = models.ForeignKey('self', null=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=2, choices=SERVICE_BODY_TYPE_CHOICES)
    description = models.TextField(null=True)
    url = models.URLField(null=True)
    world_id = models.CharField(max_length=255, null=True)


class Format(models.Model):
    id = models.BigAutoField(primary_key=True)
    source_id = models.BigIntegerField()
    root_server = models.ForeignKey(RootServer, on_delete=models.PROTECT)
    key_string = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True)
    language = models.CharField(max_length=7, default='en')
    world_id = models.CharField(max_length=255, null=True)


class Meeting(models.Model):
    id = models.BigAutoField(primary_key=True)
    source_id = models.BigIntegerField()
    root_server = models.ForeignKey(RootServer, on_delete=models.PROTECT)
    service_body = models.ForeignKey(ServiceBody, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    weekday = models.SmallIntegerField()
    start_time = models.TimeField(null=True)
    duration = models.TimeField(null=True)
    formats = models.ManyToManyField(Format)
    language = models.CharField(max_length=7, null=True)
    latitude = models.DecimalField(max_digits=11, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    published = models.BooleanField(default=False)


class MeetingInfo(models.Model):
    id = models.BigAutoField(primary_key=True)
    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE)
    email = models.EmailField(null=True)
    contact_name_1 = models.CharField(max_length=255, null=True)
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
