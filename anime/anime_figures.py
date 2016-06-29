"""
Core logic utilities for connecting figures to anime series.
"""
from collections import defaultdict
import datetime
import logging
from xml.etree import ElementTree

import dateutil.parser
import requests

from .models import AnimeSeries, Figure


logger = logging.getLogger(__name__)


ANIME_LIST_GET = 'http://myanimelist.net/malappinfo.php?u=%s&status=all&type=anime'
FIGURE_SEARCH = 'http://myfigurecollection.net/api.php?mode=search&keywords=%s'
MFC_FIGURE_ROOT_ID = '0'
RECENTLY_COMPLETED_COUNT = 10
MAX_WATCHING_COUNT = 20
RECENT_FIGURES_COUNT = 24
INCLUDE_STATUSES = ['1', '2']


class AnimeListError(Exception):
    def __init__(self, msg):
        self.msg = msg


def get_series_obj(anime_xml, mal_id_to_series, series_id_to_figures):
    mal_id = int(anime_xml.find('series_animedb_id').text)
    series_fields = {
        'image_url': anime_xml.find('series_image').text,
        'title': anime_xml.find('series_title').text
    }
    series = mal_id_to_series.get(mal_id)

    if series is None:
        series, _ = AnimeSeries.objects.get_or_create(
            mal_id=anime_xml.find('series_animedb_id').text,
            defaults=series_fields,
        )
    else:
        series.update_fields(series_fields)

    # Do a real-time figure calculation if we've never seen this series before
    last_figure_calc = series.last_figure_calc
    if not last_figure_calc:
        series, figures = recalculate_figures(series)
        series_id_to_figures[series.id] = figures
    else:
        figures = series_id_to_figures.get(series.id, [])

    return series, len(figures)


def xml_to_series_lists(series_xml, mal_id_to_series, series_id_to_figures):
    series_with_figs = []
    series_nofigs = []
    for anime_xml in series_xml:
        series, figure_count = get_series_obj(anime_xml, mal_id_to_series, series_id_to_figures)
        if figure_count:
            series_with_figs.append(series)
        else:
            series_nofigs.append(series)

    return series_with_figs, series_nofigs


def get_recent_figures(mal_ids):
    mal_figures = Figure.objects.filter(animeseries__mal_id__in=mal_ids, release_date__isnull=False)
    return list(mal_figures.order_by('-release_date')[:RECENT_FIGURES_COUNT])


def get_mal_xml(user_id):
    all_completed_xml = []  # [(anime_xml, last_updated_ts)]
    watching_xml = []
    all_mal_ids = []
    series_lookup_ids = []

    response = requests.get(ANIME_LIST_GET % user_id)
    anime_list_xml = ElementTree.fromstring(response.content)

    anime_list_error = anime_list_xml.find('error')
    if anime_list_error is not None:
        raise AnimeListError(anime_list_error.text)

    for anime_xml in anime_list_xml.findall('anime'):
        my_status = anime_xml.find('my_status').text
        if my_status not in INCLUDE_STATUSES:
            continue

        all_mal_ids.append(anime_xml.find('series_animedb_id').text)
        if anime_xml.find('my_status').text == '2':
            all_completed_xml.append((anime_xml, anime_xml.find('my_last_updated').text))

        if anime_xml.find('my_status').text == '1' and len(watching_xml) <= MAX_WATCHING_COUNT:
            watching_xml.append(anime_xml)
            series_lookup_ids.append(anime_xml.find('series_animedb_id').text)

    all_completed_xml.sort(key=lambda (_, last_updated_ts): last_updated_ts, reverse=True)
    completed_xml = [tup[0] for tup in all_completed_xml[:RECENTLY_COMPLETED_COUNT]]
    series_lookup_ids += [anime_xml.find('series_animedb_id').text for anime_xml in completed_xml]

    return watching_xml, completed_xml, series_lookup_ids, all_mal_ids


def get_bulk_lookups(series_lookup_ids):
    series_objs = AnimeSeries.objects.filter(mal_id__in=series_lookup_ids)
    mal_id_to_series = {series.mal_id: series for series in series_objs}
    figure_objs = Figure.objects.get_date_ordered().filter(animeseries__mal_id__in=series_lookup_ids)
    through_qs = AnimeSeries.figures.through.objects.filter(animeseries__mal_id__in=series_lookup_ids)
    anime_figure_mappings = through_qs.values_list('animeseries', 'figure')
    figure_id_to_series_id = defaultdict(list)
    series_id_to_figures = defaultdict(list)

    for series_id, figure_id in anime_figure_mappings:
        figure_id_to_series_id[figure_id].append(series_id)

    for figure in figure_objs:
        series_ids = figure_id_to_series_id.get(figure.id)
        for series_id in series_ids:
            series_id_to_figures[series_id].append(figure)

    return mal_id_to_series, series_id_to_figures


def get_anime_list(user_id):
    watching_xml, completed_xml, series_lookup_ids, all_mal_ids = get_mal_xml(user_id)
    mal_id_to_series, series_id_to_figures = get_bulk_lookups(series_lookup_ids)
    watching, watching_nofigs = xml_to_series_lists(
        watching_xml,
        mal_id_to_series,
        series_id_to_figures
    )
    recently_completed, completed_nofigs = xml_to_series_lists(
        completed_xml,
        mal_id_to_series,
        series_id_to_figures
    )
    return {
        'watching': watching,
        'recently_completed': recently_completed,
        'watching_nofigs': watching_nofigs,
        'completed_nofigs': completed_nofigs,
        'all_mal_ids': all_mal_ids,
        'series_id_to_figures': series_id_to_figures,
    }


def sanitize_title(title):
    return title.lstrip(' ').rstrip(' ').rstrip('(TV)')


def recalculate_figures(anime_series):
    logger.info('Querying MFC for anime %r %r', anime_series.mal_id, anime_series.title)
    figures = []
    response = requests.get(FIGURE_SEARCH % sanitize_title(anime_series.title))
    figure_list_xml = ElementTree.fromstring(response.content)
    for figure in figure_list_xml.findall('item'):
        # Only include 'Figure' type results
        if figure.find('root').find('id').text == MFC_FIGURE_ROOT_ID:
            figure_data = figure.find('data')
            release_date_str = figure_data.find('release_date').text
            if release_date_str and '0000' not in release_date_str:
                release_date_str = release_date_str.replace('-00', '-01')
                release_date = dateutil.parser.parse(release_date_str)
            else:
                release_date = None
            figure_obj = Figure.objects.create_or_update(
                mfc_id=figure_data.find('id').text,
                defaults={
                    'barcode': figure_data.find('barcode').text,
                    'name': figure_data.find('name').text,
                    'release_date': release_date,
                    'price': figure_data.find('price').text,
                    'category': figure.find('category').find('id').text,
                }
            )
            figures.append(figure_obj)
    anime_series.figures.add(*figures)
    anime_series.last_figure_calc = datetime.datetime.utcnow()
    anime_series.save(update_fields=['last_figure_calc'])
    return anime_series, figures
