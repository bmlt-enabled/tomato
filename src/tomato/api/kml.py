from django.db import models
from django.db.models import F, Func, Q
from django.db.models.functions import Cast, Concat
from django.db.models.expressions import Case, When, Value


def apply_kml_annotations(qs):
    return qs.annotate(
        address=Concat(
            'meetinginfo__location_text',
            Case(
                When(
                    (~Q(meetinginfo__location_text=None) & ~Q(meetinginfo__location_text='')) &
                    (
                        (~Q(meetinginfo__location_street=None) & ~Q(meetinginfo__location_street='')) |
                        (~Q(meetinginfo__location_city_subsection=None) & ~Q(meetinginfo__location_city_subsection='')) |
                        (~Q(meetinginfo__location_province=None) & ~Q(meetinginfo__location_province='')) |
                        (~Q(meetinginfo__location_postal_code_1=None) & ~Q(meetinginfo__location_postal_code_1='')) |
                        (~Q(meetinginfo__location_nation=None) & ~Q(meetinginfo__location_nation=''))
                    ),
                    then=Value(', ')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            'meetinginfo__location_street',
            Case(
                When(
                    (~Q(meetinginfo__location_street=None) & ~Q(meetinginfo__location_street='')) &
                    (
                        (~Q(meetinginfo__location_city_subsection=None) & ~Q(meetinginfo__location_city_subsection='')) |
                        (~Q(meetinginfo__location_province=None) & ~Q(meetinginfo__location_province='')) |
                        (~Q(meetinginfo__location_postal_code_1=None) & ~Q(meetinginfo__location_postal_code_1='')) |
                        (~Q(meetinginfo__location_nation=None) & ~Q(meetinginfo__location_nation=''))
                    ),
                    then=Value(', ')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            'meetinginfo__location_city_subsection',
            Case(
                When(
                    (~Q(meetinginfo__location_city_subsection=None) & ~Q(meetinginfo__location_city_subsection='')) &
                    (
                        (~Q(meetinginfo__location_province=None) & ~Q(meetinginfo__location_province='')) |
                        (~Q(meetinginfo__location_postal_code_1=None) & ~Q(meetinginfo__location_postal_code_1='')) |
                        (~Q(meetinginfo__location_nation=None) & ~Q(meetinginfo__location_nation=''))
                    ),
                    then=Value(', ')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            'meetinginfo__location_province',
            Case(
                When(
                    (~Q(meetinginfo__location_province=None) & ~Q(meetinginfo__location_province='')) &
                    (
                        (~Q(meetinginfo__location_postal_code_1=None) & ~Q(meetinginfo__location_postal_code_1='')) |
                        (~Q(meetinginfo__location_nation=None) & ~Q(meetinginfo__location_nation=''))
                    ),
                    then=Value(', ')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            'meetinginfo__location_postal_code_1',
            Case(
                When(
                    (~Q(meetinginfo__location_postal_code_1=None) & ~Q(meetinginfo__location_postal_code_1='')) &
                    (~Q(meetinginfo__location_nation=None) & ~Q(meetinginfo__location_nation='')),
                    then=Value(', ')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            'meetinginfo__location_nation'
        ),
        description=Concat(
            Case(
                When(weekday=1, then=Value('Sunday, ')),
                When(weekday=2, then=Value('Monday, ')),
                When(weekday=3, then=Value('Tuesday, ')),
                When(weekday=4, then=Value('Wednesday, ')),
                When(weekday=5, then=Value('Thursday, ')),
                When(weekday=6, then=Value('Friday, ')),
                When(weekday=7, then=Value('Saturday, ')),
                default=Value(''),
                output_field=models.CharField()
            ),
            Func(
                F('start_time'),
                Value('fmHH:MI AM'),
                function='to_char',
                output_field=models.CharField()
            ),
            Value(', '),
            'meetinginfo__location_street',
            Case(
                When(
                    (~Q(meetinginfo__location_street=None) & ~Q(meetinginfo__location_street='')) &
                    (
                        (~Q(meetinginfo__location_city_subsection=None) & ~Q(meetinginfo__location_city_subsection='')) |
                        (~Q(meetinginfo__location_province=None) & ~Q(meetinginfo__location_province='')) |
                        (~Q(meetinginfo__location_postal_code_1=None) & ~Q(meetinginfo__location_postal_code_1='')) |
                        (~Q(meetinginfo__location_nation=None) & ~Q(meetinginfo__location_nation=''))
                    ),
                    then=Value(', ')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            'meetinginfo__location_city_subsection',
            Case(
                When(
                    (~Q(meetinginfo__location_city_subsection=None) & ~Q(meetinginfo__location_city_subsection='')) &
                    (
                        (~Q(meetinginfo__location_province=None) & ~Q(meetinginfo__location_province='')) |
                        (~Q(meetinginfo__location_postal_code_1=None) & ~Q(meetinginfo__location_postal_code_1='')) |
                        (~Q(meetinginfo__location_nation=None) & ~Q(meetinginfo__location_nation=''))
                    ),
                    then=Value(', ')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            'meetinginfo__location_province',
            Case(
                When(
                    (~Q(meetinginfo__location_province=None) & ~Q(meetinginfo__location_province='')) &
                    (
                        (~Q(meetinginfo__location_postal_code_1=None) & ~Q(meetinginfo__location_postal_code_1='')) |
                        (~Q(meetinginfo__location_nation=None) & ~Q(meetinginfo__location_nation=''))
                    ),
                    then=Value(', ')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            'meetinginfo__location_postal_code_1',
            Case(
                When(
                    (~Q(meetinginfo__location_postal_code_1=None) & ~Q(meetinginfo__location_postal_code_1='')) &
                    (~Q(meetinginfo__location_nation=None) & ~Q(meetinginfo__location_nation='')),
                    then=Value(', ')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            'meetinginfo__location_nation',
            Case(
                When(
                    ~Q(meetinginfo__location_info=None) & ~Q(meetinginfo__location_info=''),
                    then=Value(' ')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            Case(
                When(
                    (~Q(meetinginfo__location_info=None) & ~Q(meetinginfo__location_info='')) &
                    (
                        (~Q(meetinginfo__location_street=None) & ~Q(meetinginfo__location_street='')) |
                        (~Q(meetinginfo__location_city_subsection=None) & ~Q(meetinginfo__location_city_subsection='')) |
                        (~Q(meetinginfo__location_province=None) & ~Q(meetinginfo__location_province='')) |
                        (~Q(meetinginfo__location_postal_code_1=None) & ~Q(meetinginfo__location_postal_code_1='')) |
                        (~Q(meetinginfo__location_nation=None) & ~Q(meetinginfo__location_nation=''))
                    ),
                    then=Value('(')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            'meetinginfo__location_info',
            Case(
                When(
                    (~Q(meetinginfo__location_info=None) & ~Q(meetinginfo__location_info='')) &
                    (
                        (~Q(meetinginfo__location_street=None) & ~Q(meetinginfo__location_street='')) |
                        (~Q(meetinginfo__location_city_subsection=None) & ~Q(meetinginfo__location_city_subsection='')) |
                        (~Q(meetinginfo__location_province=None) & ~Q(meetinginfo__location_province='')) |
                        (~Q(meetinginfo__location_postal_code_1=None) & ~Q(meetinginfo__location_postal_code_1='')) |
                        (~Q(meetinginfo__location_nation=None) & ~Q(meetinginfo__location_nation=''))
                    ),
                    then=Value(')')
                ),
                default=Value(''),
                output_field=models.CharField()
            ),
            output_field=models.CharField()
        ),
        coordinates=Concat(
            Cast('longitude', models.FloatField()),
            Value(','),
            Cast('latitude', models.FloatField()),
            Value(',0'),
            output_field=models.CharField()
        )
    )
