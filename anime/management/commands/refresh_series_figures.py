import datetime
import logging

from django.core.management.base import NoArgsCommand

from ...anime_figures import recalculate_figures
from ...models import AnimeSeries

logger = logging.getLogger(__name__)


class Command(NoArgsCommand):
    """
    Performs a new search for figures for all anime series which have
    not been refreshed in over 48 hours.

    Intended to be run as a cron job.
    """
    def handle_noargs(self, **options):
        two_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=2)
        series_to_refresh = AnimeSeries.objects.filter(last_figure_calc__lt=two_days_ago)
        counter = 0

        for series in series_to_refresh:
            recalculate_figures(series)
            counter += 1

        logger.info('refreshed %d series', counter)
