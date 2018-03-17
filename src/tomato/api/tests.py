import csv
import datetime
import json
import io
import urllib.parse
from django.conf import settings
from django.db import models
from django.test import TestCase
from django.urls import reverse
from xml.etree import ElementTree as ET
from .models import Format, Meeting, MeetingInfo
from .views import (field_keys, meeting_field_map, model_get_value, parse_time_params,
                    parse_timedelta_params, service_bodies_field_map, valid_meeting_search_keys)


is_spatialite = 'spatialite' in settings.DATABASES['default']['ENGINE']


class GetSearchResultsTests(TestCase):
    fixtures = ['testdata']

    # json/xml/csv
    def test_get_search_results_json(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        response = json.loads(response.content)
        self.assertEqual(len(response), 10)
        meeting = response[0]
        for key in meeting.keys():
            self.assertIn(key, meeting_field_map.keys())
        for key in meeting_field_map.keys():
            value = meeting_field_map[key]
            if len(value) > 1 and callable(value[1]):
                continue
            self.assertIn(key, meeting.keys())

    def test_get_search_results_xml(self):
        url = reverse('semantic-query', kwargs={'format': 'xml'})
        url += '?switcher=GetSearchResults'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
        response = ET.fromstring(response.content)
        self.assertEqual(len(response.findall('./{http://testserver}row')), 10)

    def test_get_search_results_csv(self):
        url = reverse('semantic-query', kwargs={'format': 'csv'})
        url += '?switcher=GetSearchResults'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        s = io.StringIO(response.content.decode(response.charset))
        try:
            reader = csv.DictReader(s)
            for field_name in reader.fieldnames:
                self.assertIn(field_name, meeting_field_map.keys())
            num_rows = 0
            for row in reader:
                num_rows += 1
            self.assertEqual(num_rows, 10)
        finally:
            s.close()

    # formats filters
    def test_get_search_results_with_formats(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&get_used_formats=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(isinstance(response, dict))
        self.assertTrue('formats' in response)
        self.assertTrue('meetings' in response)
        self.assertEqual(len(response['meetings']), 10)
        for meeting in response['meetings']:
            for meeting_format in meeting['formats'].split(','):
                if meeting_format == '':
                    continue
                for format in response['formats']:
                    if format['key_string'] == meeting_format:
                        break
                else:
                    self.fail('Meeting format {} not found'.format(meeting_format))
        for format in response['formats']:
            for meeting in response['meetings']:
                found = False
                for meeting_format in meeting['formats'].split(','):
                    if meeting_format == '':
                        continue
                    if format['key_string'] == meeting_format:
                        found = True
                        break
                if found:
                    break
            else:
                self.fail('Format {} not found with a meeting'.format(format))

    def test_get_search_results_with_formats_formats_only(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&get_used_formats=1&get_formats_only=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue('formats' in response)
        self.assertFalse('meetings' in response)
        self.assertTrue(len(response['formats']), 12)

    # weekdays filters
    def test_get_search_results_weekdays_include_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&weekdays=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 1)
        for meeting in response:
            self.assertEqual(meeting['weekday_tinyint'], '2')

    def test_get_search_results_weekdays_include_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&weekdays[]=1&weekdays[]=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 1)
        found_one = False
        found_two = False
        for meeting in response:
            if meeting['weekday_tinyint'] == '1':
                found_one = True
            elif meeting['weekday_tinyint'] == '2':
                found_two = True
            else:
                self.fail('Unexpected weekday found')
        self.assertTrue(found_one)
        self.assertTrue(found_two)

    def test_get_search_results_weekdays_include_none_found(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&weekdays=7'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) == 0)

    def test_get_search_results_weekdays_exclude_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&weekdays=-2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 1)
        for meeting in response:
            self.assertNotEqual(meeting['weekday_tinyint'], '2')

    def test_get_search_results_weekdays_exclude_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&weekdays[]=-1&weekdays[]=-2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 1)
        for meeting in response:
            self.assertNotEqual(meeting['weekday_tinyint'], '1')
            self.assertNotEqual(meeting['weekday_tinyint'], '2')

    # services filters
    def test_get_search_results_services_include_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&services=5'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        for meeting in response:
            self.assertEqual(meeting['service_body_bigint'], '5')

    def test_get_search_results_services_include_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&services[]=5&services[]=4'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        found_four = False
        found_five = False
        for meeting in response:
            if meeting['service_body_bigint'] == '4':
                found_four = True
            elif meeting['service_body_bigint'] == '5':
                found_five = True
            else:
                self.fail('Unexpected service body found')
        self.assertTrue(found_four)
        self.assertTrue(found_five)

    def test_get_search_results_services_include_none_found(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&services=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) == 0)

    def test_get_search_results_services_exclude_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&services=-5'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        for meeting in response:
            self.assertNotEqual(meeting['service_body_bigint'], '5')

    def test_get_search_results_services_exclude_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&services[]=-5&services[]=-4'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        for meeting in response:
            self.assertNotEqual(meeting['service_body_bigint'], '4')
            self.assertNotEqual(meeting['service_body_bigint'], '5')

    # formats filters
    def test_get_search_results_formats_include_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&formats=29'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        f = Format.objects.get(id=29)
        for meeting in response:
            self.assertIn(f.key_string, meeting['formats'])

    def test_get_search_results_formats_include_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&formats[]=9&formats[]=12'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        f_nine = Format.objects.get(id=9)
        f_twelve = Format.objects.get(id=12)
        for meeting in response:
            self.assertIn(f_nine.key_string, meeting['formats'])
            self.assertIn(f_twelve.key_string, meeting['formats'])

    def test_get_search_results_formats_include_none_found(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&formats=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) == 0)

    def test_get_search_results_formats_exclude_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&formats=-29&root_server_ids=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        f = Format.objects.get(id=29)
        for meeting in response:
            self.assertNotIn(f.key_string, meeting['formats'])

    def test_get_search_results_formats_exclude_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&formats[]=-9&formats[]=-12&root_server_ids=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        f_nine = Format.objects.get(id=9)
        f_twelve = Format.objects.get(id=12)
        for meeting in response:
            self.assertNotIn(f_nine.key_string, meeting['formats'])
            self.assertNotIn(f_twelve.key_string, meeting['formats'])

    # root_server_ids filters
    def test_get_search_results_root_server_ids_include_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&root_server_ids=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        for meeting in response:
            self.assertEqual(meeting['root_server_id'], '1')

    def test_get_search_results_root_server_ids_include_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&root_server_ids[]=1&root_server_ids[]=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        found_one = False
        found_two = False
        for meeting in response:
            if meeting['root_server_id'] == '1':
                found_one = True
            elif meeting['root_server_id'] == '2':
                found_two = True
        self.assertTrue(found_one)
        self.assertTrue(found_two)

    def test_get_search_results_root_server_ids_include_found_none(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&root_server_ids=3'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) == 0)

    def test_get_search_results_root_server_ids_exclude_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&root_server_ids=-2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        for meeting in response:
            self.assertEqual(meeting['root_server_id'], '1')

    def test_get_search_results_root_server_ids_exclude_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&root_server_ids[]=-1&root_server_ids[]=-2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) == 0)

    # meeting_key + meeting_key_value
    def test_get_search_results_meeting_key(self):
        def get_field(field_name):
            if field_name.startswith('meetinginfo'):
                field_name = field_name.split('.')[-1]
                for field in MeetingInfo._meta.fields:
                    if field.attname == field_name:
                        return field
            else:
                for field in Meeting._meta.fields:
                    if field.attname == field_name:
                        return field
            return None

        for meeting_key in valid_meeting_search_keys:
            if is_spatialite and meeting_key == 'duration_time':
                continue
            model_field = meeting_field_map.get(meeting_key)[0]
            qs = Meeting.objects.exclude(**{model_field.replace('.', '__'): None})
            actual_field = get_field(model_field)
            t = type(actual_field)
            if t in (models.CharField, models.TextField):
                qs = qs.exclude(**{model_field.replace('.', '__'): ''})
            meeting = qs[0]
            value = model_get_value(meeting, model_field)
            url = reverse('semantic-query', kwargs={'format': 'json'})
            url += '?switcher=GetSearchResults&'
            url += urllib.parse.urlencode({'meeting_key': meeting_key, 'meeting_key_value': value})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            response = json.loads(response.content)
            self.assertTrue(len(response) > 0)
            for meeting in response:
                self.assertTrue(meeting[meeting_key] == value)

    # data_field_keys
    def test_get_search_results_data_field_keys(self):
        for data_field_key in field_keys:
            if is_spatialite and data_field_key == 'formats':
                continue
            url = reverse('semantic-query', kwargs={'format': 'json'})
            url += '?switcher=GetSearchResults&'
            url += urllib.parse.urlencode({'data_field_key': data_field_key})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            response = json.loads(response.content)
            self.assertTrue(len(response) > 0)
            for meeting in response:
                returned_keys = list(meeting.keys())
                self.assertEqual(len(returned_keys), 1)
                self.assertEqual(returned_keys[0], data_field_key)

        for i in range(len(field_keys)):
            if i >= len(field_keys) - 1:
                continue
            data_field_keys = [field_keys[i], field_keys[i + 1]]
            if is_spatialite and 'formats' in data_field_keys:
                continue
            url = reverse('semantic-query', kwargs={'format': 'json'})
            url += '?switcher=GetSearchResults&'
            url += urllib.parse.urlencode({'data_field_key': ','.join(data_field_keys)})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            response = json.loads(response.content)
            self.assertTrue(len(response) > 0)
            for meeting in response:
                returned_keys = list(meeting.keys())
                self.assertEqual(len(returned_keys), 2)
                self.assertEqual(returned_keys[0], data_field_keys[0])
                self.assertEqual(returned_keys[1], data_field_keys[1])

    # starts after
    def test_get_search_results_starts_after_hour(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&StartsAfterH=12'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        for meeting in response:
            start_time = meeting.get('start_time')
            hour = start_time.split(':')[0]
            self.assertTrue(int(hour) > 12)

    def test_get_search_results_starts_after_hour_and_minute(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&StartsAfterH=10&StartsAfterM=30'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        for meeting in response:
            start_time = meeting.get('start_time')
            hour = start_time.split(':')[0]
            minute = start_time.split(':')[1]
            self.assertTrue(int(hour) > 9)
            if int(hour) == 10:
                self.assertTrue(int(minute) > 30)

    # starts before
    def test_get_search_results_starts_before_hour(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&StartsBeforeH=12'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        for meeting in response:
            start_time = meeting.get('start_time')
            hour = start_time.split(':')[0]
            self.assertTrue(int(hour) < 12)

    def test_get_search_results_starts_before_hour_and_minute(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&StartsBeforeH=10&StartsBeforeM=30'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        for meeting in response:
            start_time = meeting.get('start_time')
            hour = start_time.split(':')[0]
            minute = start_time.split(':')[1]
            self.assertTrue(int(hour) < 11)
            if int(hour) == 10:
                self.assertTrue(int(minute) < 30)

    # ends before
    def test_get_search_results_ends_before_hour(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&EndsBeforeH=12'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        for meeting in response:
            start_time = meeting.get('start_time').split(':')
            start_time = parse_time_params(start_time[0], start_time[1])
            duration = meeting.get('duration_time').split(':')
            duration = parse_timedelta_params(duration[0], duration[1])
            end_time = datetime.datetime.combine(datetime.datetime.today(), start_time) + duration
            end_time = end_time.time()
            self.assertTrue(end_time.hour < 12)

    def test_get_search_results_ends_before_hour_and_minute(self):
        if is_spatialite:
            return
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&EndsBeforeH=10&EndsBeforeM=30'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(len(response) > 0)
        for meeting in response:
            start_time = meeting.get('start_time').split(':')
            start_time = parse_time_params(start_time[0], start_time[1])
            duration = meeting.get('duration_time').split(':')
            duration = parse_timedelta_params(duration[0], duration[1])
            end_time = datetime.datetime.combine(datetime.datetime.today(), start_time) + duration
            end_time = end_time.time()
            self.assertTrue(end_time.hour < 12)


class GetServiceBodiesTests(TestCase):
    fixtures = ['testdata']

    def test_get_service_bodies_json(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetServiceBodies'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        response = json.loads(response.content)
        self.assertEqual(len(response), 29)
        body = response[0]
        for key in body.keys():
            self.assertIn(key, service_bodies_field_map.keys())
        for key in service_bodies_field_map.keys():
            self.assertIn(key, body.keys())

    def test_get_service_bodies_xml(self):
        url = reverse('semantic-query', kwargs={'format': 'xml'})
        url += '?switcher=GetServiceBodies'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
        response = ET.fromstring(response.content)
        self.assertEqual(len(response.findall('./row')), 29)

    def test_get_service_bodies_csv(self):
        url = reverse('semantic-query', kwargs={'format': 'csv'})
        url += '?switcher=GetServiceBodies'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        s = io.StringIO(response.content.decode(response.charset))
        try:
            reader = csv.DictReader(s)
            for field_name in reader.fieldnames:
                self.assertIn(field_name, service_bodies_field_map.keys())
            num_rows = 0
            for row in reader:
                num_rows += 1
            self.assertEqual(num_rows, 29)
        finally:
            s.close()

    def test_service_bodies_parent_is_0(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetServiceBodies'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        found_zero = False
        for body in response:
            self.assertTrue(body['parent_id'] is not None)
            if body['parent_id'] == '0':
                found_zero = True
        self.assertTrue(found_zero)

    def test_service_bodies_root_server_id(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetServiceBodies&root_server_id=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        for body in response:
            self.assertEqual(body['root_server_id'], '1')
