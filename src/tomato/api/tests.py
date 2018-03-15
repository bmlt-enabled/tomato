import csv
import json
import io
import urllib.parse
from django.db import models
from django.test import TestCase
from django.urls import reverse
from mock import patch
from requests.models import Response
from xml.etree import ElementTree as ET
from .models import Format, Meeting, MeetingInfo
from .views import (meeting_field_map, model_get_value, service_bodies_field_map, valid_meeting_search_keys,
                    GeocodeAPIException)


class GetSearchResultsTests(TestCase):
    fixtures = ['testdata']

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
            if meeting_key == 'duration_time':
                # Need to see what format BMLT expects duration fields to come in as for this query
                # Interestingly, this test passes as is when using postgres, but fails using spatialite
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
