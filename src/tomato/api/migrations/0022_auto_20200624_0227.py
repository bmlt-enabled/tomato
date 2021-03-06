# Generated by Django 2.2.8 on 2020-06-24 02:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0021_auto_20200623_2322'),
    ]

    operations = [
        migrations.AlterField(
            model_name='translatedformat',
            name='format',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='translatedformats', related_query_name='translatedformats', to='api.Format'),
        ),
        migrations.AlterField(
            model_name='translatedformat',
            name='language',
            field=models.CharField(db_index=True, default='en', max_length=7),
        ),
    ]
