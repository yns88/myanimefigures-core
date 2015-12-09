from __future__ import unicode_literals

from django.db import models


class AnimeManager(models.Manager):
    """
    Object creation / querying helpers.
    """
    def create_or_update(self, defaults=None, **kwargs):
        defaults = defaults or {}
        obj, created = self.get_or_create(defaults, **kwargs)
        if not created:
            obj_dirty = False
            for k, v in defaults.iteritems():
                if hasattr(object, k) and getattr(object, k) != v:
                    setattr(obj, k, v)
                    obj_dirty = True

            if obj_dirty:
                obj.save()

        return obj


class FigureManager(AnimeManager):
    def get_date_ordered(self):
        return self.order_by('-release_date')


class AnimeSeries(models.Model):
    mal_id = models.IntegerField(unique=True)
    image_url = models.CharField(max_length=255, null=True)
    title = models.CharField(max_length=255, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_figure_calc = models.DateTimeField(null=True)
    figures = models.ManyToManyField('Figure')

    objects = AnimeManager()


class Figure(models.Model):
    mfc_id = models.IntegerField(unique=True)
    barcode = models.CharField(max_length=16, null=True)
    name = models.CharField(max_length=255)
    release_date = models.DateTimeField(null=True)
    price = models.IntegerField(null=True)  # in JPY
    category = models.IntegerField(null=True)
    last_updated = models.DateTimeField(auto_now=True)

    objects = FigureManager()
