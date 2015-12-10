# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2015-12-09 01:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anime', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnimeSeries',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mal_id', models.IntegerField(unique=True)),
                ('image_url', models.CharField(max_length=255, null=True)),
                ('title', models.CharField(max_length=255, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('last_figure_calc', models.DateTimeField(null=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='anime',
            name='figures',
        ),
        migrations.AlterField(
            model_name='figure',
            name='mfc_id',
            field=models.IntegerField(unique=True),
        ),
        migrations.DeleteModel(
            name='Anime',
        ),
        migrations.AddField(
            model_name='animeseries',
            name='figures',
            field=models.ManyToManyField(to='anime.Figure'),
        ),
    ]