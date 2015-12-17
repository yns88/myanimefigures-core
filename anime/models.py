from __future__ import unicode_literals

from django.db import models


FIGURE_URL = 'http://s1.tsuki-board.net/pics/figure/%s.jpg'
TRUNCATE_NAME_LEN = 50


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
        qs = self.order_by('-release_date')
        qs_null_annotated = qs.extra(select={'release_date_null': 'release_date is null'})
        return qs_null_annotated.extra(order_by=['-release_date', 'release_date_null'])


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
    release_date = models.DateTimeField(null=True, db_index=True)
    price = models.IntegerField(null=True)  # in JPY
    category = models.IntegerField(null=True)
    last_updated = models.DateTimeField(auto_now=True)

    objects = FigureManager()

    @property
    def image_url(self):
        return FIGURE_URL % self.mfc_id

    @property
    def truncated_name(self):
        if len(unicode(self.name)) > TRUNCATE_NAME_LEN:
            return unicode(self.name)[:TRUNCATE_NAME_LEN - 3] + u'...'
        return self.name
