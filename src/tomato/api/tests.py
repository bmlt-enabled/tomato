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
from .semantic import model_get_value
from .views import (field_keys, meeting_field_map, parse_time_params, distance_field_keys,
                    parse_timedelta_params, service_bodies_field_map, valid_meeting_search_keys)


is_spatialite = 'spatialite' in settings.DATABASES['default']['ENGINE']


class GetSearchResultsTests(TestCase):
    fixtures = ['testdata']

    # json/xml/csv
    def test_get_search_results_json(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&root_server_ids=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertEqual(len(response), 5)
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
        url += '?switcher=GetSearchResults&root_server_ids=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
        response = ET.fromstring(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertEqual(len(response.findall('./{http://testserver}row')), 5)

    def test_get_search_results_csv(self):
        url = reverse('semantic-query', kwargs={'format': 'csv'})
        url += '?switcher=GetSearchResults&root_server_ids=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        s = io.StringIO(''.join([b.decode('utf-8') for b in response.streaming_content]))
        try:
            reader = csv.DictReader(s)
            for field_name in reader.fieldnames:
                self.assertIn(field_name, meeting_field_map.keys())
            num_rows = 0
            for row in reader:
                num_rows += 1
            self.assertEqual(num_rows, 5)
        finally:
            s.close()

    # formats filters
    def test_get_search_results_with_formats(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&root_server_ids=1&get_used_formats=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(isinstance(response, dict))
        self.assertTrue('formats' in response)
        self.assertTrue('meetings' in response)
        self.assertEqual(len(response['meetings']), 5)
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
        url += '?switcher=GetSearchResults&root_server_ids=1&get_used_formats=1&get_formats_only=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue('formats' in response)
        self.assertFalse('meetings' in response)
        self.assertTrue(len(response['formats']) == 8)

    # weekdays filters
    def test_get_search_results_weekdays_include_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&weekdays=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 1)
        for meeting in response:
            self.assertEqual(meeting['weekday_tinyint'], '2')

    def test_get_search_results_weekdays_include_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&weekdays[]=1&weekdays[]=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) == 0)

    def test_get_search_results_weekdays_exclude_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&weekdays=-2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 1)
        for meeting in response:
            self.assertNotEqual(meeting['weekday_tinyint'], '2')

    def test_get_search_results_weekdays_exclude_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&weekdays[]=-1&weekdays[]=-2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        for meeting in response:
            self.assertEqual(meeting['service_body_bigint'], '5')

    def test_get_search_results_services_include_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&services[]=5&services[]=4'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) == 0)

    def test_get_search_results_services_exclude_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&services=-5'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        for meeting in response:
            self.assertNotEqual(meeting['service_body_bigint'], '5')

    def test_get_search_results_services_exclude_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&services[]=-5&services[]=-4'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        f = Format.objects.get(id=29)
        for meeting in response:
            for tf in f.translatedformats.all():
                self.assertIn(tf.key_string, meeting['formats'])

    def test_get_search_results_formats_include_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&formats[]=9&formats[]=12'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        f_nine = Format.objects.get(id=9)
        f_twelve = Format.objects.get(id=12)
        for meeting in response:
            for tf in f_nine.translatedformats.filter(language='en'):
                self.assertIn(tf.key_string, meeting['formats'])
            for tf in f_twelve.translatedformats.filter(language='en'):
                self.assertIn(tf.key_string, meeting['formats'])

    def test_get_search_results_formats_include_none_found(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&formats=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) == 0)

    def test_get_search_results_formats_exclude_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&formats=-29&root_server_ids=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        f = Format.objects.get(id=29)
        for meeting in response:
            for tf in f.translatedformats.all():
                self.assertNotIn(tf.key_string, meeting['formats'])

    def test_get_search_results_formats_exclude_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&formats[]=-9&formats[]=-12&root_server_ids=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        f_nine = Format.objects.get(id=9)
        f_twelve = Format.objects.get(id=12)
        for meeting in response:
            for tf in f_nine.translatedformats.all():
                self.assertNotIn(tf.key_string, meeting['formats'])
            for tf in f_twelve.translatedformats.all():
                self.assertNotIn(tf.key_string, meeting['formats'])

    # root_server_ids filters
    def test_get_search_results_root_server_ids_include_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&root_server_ids=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        for meeting in response:
            self.assertEqual(meeting['root_server_id'], '1')

    def test_get_search_results_root_server_ids_include_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&root_server_ids[]=1&root_server_ids[]=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) == 0)

    def test_get_search_results_root_server_ids_exclude_single(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&root_server_ids=-2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        for meeting in response:
            self.assertEqual(meeting['root_server_id'], '1')

    def test_get_search_results_root_server_ids_exclude_multiple(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&root_server_ids[]=-1&root_server_ids[]=-2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
            qs = list(qs)
            meeting = qs[0]
            value = model_get_value(meeting, model_field)
            url = reverse('semantic-query', kwargs={'format': 'json'})
            url += '?switcher=GetSearchResults&'
            url += urllib.parse.urlencode({'meeting_key': meeting_key, 'meeting_key_value': value})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
            self.assertTrue(len(response) > 0)
            for meeting in response:
                self.assertTrue(meeting[meeting_key] == value)

    # data_field_keys
    def test_get_search_results_data_field_keys(self):
        for data_field_key in field_keys:
            if is_spatialite and data_field_key in ('formats', 'format_shared_id_list'):
                continue
            url = reverse('semantic-query', kwargs={'format': 'json'})
            url += '?switcher=GetSearchResults&'
            url += urllib.parse.urlencode({'data_field_key': data_field_key})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
            self.assertTrue(len(response) > 0)
            for meeting in response:
                returned_keys = list(meeting.keys())
                if data_field_key in distance_field_keys:
                    self.assertEqual(len(returned_keys), 0)
                else:
                    self.assertEqual(len(returned_keys), 1)
                    self.assertEqual(returned_keys[0], data_field_key)

        for i in range(len(field_keys)):
            if i >= len(field_keys) - 1:
                continue
            data_field_keys = [field_keys[i], field_keys[i + 1]]
            if is_spatialite and ('formats' in data_field_keys or 'format_shared_id_list' in data_field_keys):
                continue
            url = reverse('semantic-query', kwargs={'format': 'json'})
            url += '?switcher=GetSearchResults&'
            url += urllib.parse.urlencode({'data_field_key': ','.join(data_field_keys)})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
            self.assertTrue(len(response) > 0)
            for meeting in response:
                returned_keys = list(meeting.keys())
                contains_distance_keys = set(data_field_keys).intersection(set(distance_field_keys))
                if contains_distance_keys:
                    num_distance_keys = len(contains_distance_keys)
                    self.assertEqual(len(returned_keys), 2 - num_distance_keys)
                else:
                    self.assertEqual(len(returned_keys), 2)
                    self.assertEqual(returned_keys[0], data_field_keys[0])
                    self.assertEqual(returned_keys[1], data_field_keys[1])

    def test_get_search_results_data_field_keys_distance_keys(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        data_field_keys = ['distance_in_km', 'distance_in_miles']
        url += '?switcher=GetSearchResults&lat_val=21.3391774&long_val=-157.7036977&'
        url += urllib.parse.urlencode({'data_field_key': ','.join(data_field_keys)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        if is_spatialite:
            return
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&EndsBeforeH=12'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        for meeting in response:
            start_time = meeting.get('start_time').split(':')
            start_time = parse_time_params(start_time[0], start_time[1])
            duration = meeting.get('duration_time').split(':')
            duration = parse_timedelta_params(duration[0], duration[1])
            end_time = datetime.datetime.combine(datetime.datetime.today(), start_time) + duration
            end_time = end_time.time()
            self.assertTrue(end_time.hour < 12)

    # min duration
    def test_get_search_results_min_duration_hour(self):
        if is_spatialite:
            return
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&MinDurationH=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        for meeting in response:
            duration = meeting.get('duration_time').split(':')
            duration = parse_timedelta_params(duration[0], duration[1])
            self.assertTrue(duration >= datetime.timedelta(hours=2))

    def test_get_search_results_min_duration_hour_and_minute(self):
        if is_spatialite:
            return
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&MinDurationH=1&MinDurationM=30'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        for meeting in response:
            duration = meeting.get('duration_time').split(':')
            duration = parse_timedelta_params(duration[0], duration[1])
            self.assertTrue(duration >= datetime.timedelta(hours=1, minutes=30))

    # max duration
    def test_get_search_results_max_duration_hour(self):
        if is_spatialite:
            return
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&MaxDurationH=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        for meeting in response:
            duration = meeting.get('duration_time').split(':')
            duration = parse_timedelta_params(duration[0], duration[1])
            self.assertTrue(duration <= datetime.timedelta(hours=1))

    def test_get_search_results_max_duration_hour_and_minute(self):
        if is_spatialite:
            return
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&MaxDurationH=1&MaxDurationM=30'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 0)
        for meeting in response:
            duration = meeting.get('duration_time').split(':')
            duration = parse_timedelta_params(duration[0], duration[1])
            self.assertTrue(duration <= datetime.timedelta(hours=1, minutes=30))

    # geo_width positive
    def test_get_search_results_geo_width_positive_found_one(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&lat_val=21.3391774&long_val=-157.7036977&geo_width=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) == 1)

    def test_get_search_results_geo_width_positive_found_several(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&lat_val=21.33190206&long_val=-157.69392371&geo_width=100'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 1)

    def test_get_search_results_geo_width_distance_included(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&lat_val=21.3391774&long_val=-157.7036977&geo_width=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) == 1)
        self.assertTrue('distance_in_km' in response[0])
        self.assertTrue('distance_in_miles' in response[0])

    # geo_width_km positive
    def test_get_search_results_geo_width_positive_found_none(self):
        # This would return a meeting for miles, but not for km
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&lat_val=21.3391774&long_val=-157.7036977&geo_width_km=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) == 0)

    def test_get_search_results_geo_width_km_positive_found_one(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&lat_val=21.3363692&long_val=-157.701509&geo_width_km=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) == 1)

    def test_get_search_results_geo_width_km_positive_found_several(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&lat_val=21.33190206&long_val=-157.69392371&geo_width_km=100'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 1)

    def test_get_search_results_geo_width_km_distance_included(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&lat_val=21.3363692&long_val=-157.701509&geo_width_km=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) == 1)
        self.assertTrue('distance_in_km' in response[0])
        self.assertTrue('distance_in_miles' in response[0])

    # geo_width and geo_width_km negative
    def test_get_search_results_geo_width_negative(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&lat_val=21.3391774&long_val=-157.7036977&geo_width=-5'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) == 5)

    def test_get_search_results_geo_width_km_negative(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&lat_val=21.3391774&long_val=-157.7036977&geo_width=-6'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) == 6)

    # sort results by distance
    def test_get_search_results_sort_results_by_distance(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&lat_val=21.33190206&long_val=-157.69392371&geo_width_km=1000000000&sort_results_by_distance=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertTrue(len(response) > 1)
        prev_miles = None
        prev_km = None
        for meeting in response:
            miles = float(meeting['distance_in_miles'])
            km = float(meeting['distance_in_km'])
            if prev_miles:
                self.assertTrue(miles >= prev_miles)
            if prev_km:
                self.assertTrue(km >= prev_km)
            prev_miles = miles
            prev_km = km

    def test_get_search_results_sort_keys(self):
        for sort_key in [k for k in field_keys if k not in distance_field_keys]:
            if sort_key in ('formats', 'format_shared_id_list',):
                continue  # not sure how this behaves... don't care
            url = reverse('semantic-query', kwargs={'format': 'json'})
            url += '?switcher=GetSearchResults&'
            url += urllib.parse.urlencode({'sort_keys': sort_key})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
            self.assertTrue(len(response) > 0)
            prev_sort_value = None
            for meeting in response:
                sort_value = meeting.get(sort_key)
                try:
                    sort_value = float(sort_value)
                except ValueError:
                    pcs = sort_value.split(':')
                    if len(pcs) == 3 and len(pcs[0]) == 2 and len(pcs[1]) == 2:
                        try:
                            sort_value = parse_timedelta_params(pcs[0], pcs[1])
                        except ValueError:
                            self.fail('Invalid time')
                if prev_sort_value:
                    self.assertTrue(sort_value >= prev_sort_value)
                prev_sort_value = sort_value

        for i in range(len(field_keys) - len(distance_field_keys)):
            if i >= len(field_keys) - len(distance_field_keys) - 1:
                continue
            sort_keys = [field_keys[i], field_keys[i + 1]]
            if 'formats' in sort_keys:
                continue
            url = reverse('semantic-query', kwargs={'format': 'json'})
            url += '?switcher=GetSearchResults&'
            url += urllib.parse.urlencode({'sort_keys': ','.join(sort_keys)})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
            self.assertTrue(len(response) > 0)
            prev_sort_value = None
            for meeting in response:
                sort_value = meeting.get(sort_keys[0])
                try:
                    sort_value = float(sort_value)
                except ValueError:
                    pcs = sort_value.split(':')
                    if len(pcs) == 3 and len(pcs[0]) == 2 and len(pcs[1]) == 2:
                        try:
                            sort_value = parse_timedelta_params(pcs[0], pcs[1])
                        except ValueError:
                            self.fail('Invalid time')
                if prev_sort_value:
                    self.assertTrue(sort_value >= prev_sort_value)
                prev_sort_value = sort_value


class GetServiceBodiesTests(TestCase):
    fixtures = ['testdata']

    def test_get_service_bodies_json(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetServiceBodies'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertEqual(len(response), 29)
        body = response[0]
        for key in body.keys():
            self.assertIn(key, service_bodies_field_map.keys())
        for key in service_bodies_field_map.keys():
            self.assertIn(key, body.keys())

    def test_get_service_bodies_json_parents(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetServiceBodies&services=8&parents=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertEqual(len(response), 3)
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
        response = ET.fromstring(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertEqual(len(response.findall('./row')), 29)

    def test_get_service_bodies_csv(self):
        url = reverse('semantic-query', kwargs={'format': 'csv'})
        url += '?switcher=GetServiceBodies'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        s = io.StringIO(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
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
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        for body in response:
            self.assertEqual(body['root_server_id'], '1')

    def test_get_search_results_one_meeting(self):
        url = reverse('semantic-query', kwargs={'format': 'json'})
        url += '?switcher=GetSearchResults&meeting_ids[]=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        response = json.loads(''.join([b.decode('utf-8') for b in response.streaming_content]))
        self.assertEqual(len(response), 1)
        meeting = response[0]
        for key in meeting.keys():
            self.assertIn(key, meeting_field_map.keys())
        for key in meeting_field_map.keys():
            value = meeting_field_map[key]
            if len(value) > 1 and callable(value[1]):
                continue
            self.assertIn(key, meeting.keys())
