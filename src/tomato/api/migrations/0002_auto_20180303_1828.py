# Generated by Django 2.0.2 on 2018-03-03 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicebody',
            name='type',
            field=models.CharField(choices=[('AS', 'Area'), ('MA', 'Metro'), ('RS', 'Region')], max_length=2),
        ),
    ]
