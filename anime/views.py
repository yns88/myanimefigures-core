import datetime
import dateutil.parser
import logging
from xml.etree import ElementTree

from django.contrib import messages
from django.http.response import HttpResponseRedirect
from django.shortcuts import render
import requests

from .models import AnimeSeries, Figure

logger = logging.getLogger(__name__)


ANIME_LIST_GET = 'http://myanimelist.net/malappinfo.php?u=%s&status=all&type=anime'
FIGURE_SEARCH = 'http://myfigurecollection.net/api.php?mode=search&keywords=%s'
RECENTLY_COMPLETED_COUNT = 10
MAX_WATCHING_COUNT = 20
RECENT_FIGURES_COUNT = 12
MFC_FIGURE_ROOT_ID = '0'
FIGURE_CACHE_DURATION = datetime.timedelta(days=1)
INCLUDE_STATUSES = ['1', '2']


class AnimeListError(Exception):
    def __init__(self, msg):
        self.msg = msg


def index(request):
    return render(request, 'anime/index.html', {})


def sanitize_title(title):
    return title.lstrip(' ').rstrip(' ').rstrip('(TV)')


def get_series_obj(anime_xml):
    series = AnimeSeries.objects.create_or_update(
        mal_id=anime_xml.find('series_animedb_id').text,
        defaults={
            'image_url': anime_xml.find('series_image').text,
            'title': anime_xml.find('series_title').text
        },
    )
    # Make sure figures are up to date
    last_figure_calc = series.last_figure_calc
    cache_cutoff = datetime.datetime.utcnow() - FIGURE_CACHE_DURATION
    if not last_figure_calc or last_figure_calc < cache_cutoff:
        series, figure_count = recalculate_figures(series)
    else:
        figure_count = series.figures.count()

    return series, figure_count


def get_recent_figures(mal_ids):
    mal_figures = Figure.objects.filter(animeseries__mal_id__in=mal_ids)
    return list(mal_figures.order_by('-release_date')[:RECENT_FIGURES_COUNT])[::-1]


def get_anime_list(user_id):
    response = requests.get(ANIME_LIST_GET % user_id)
    watching = []
    watching_nofigs = []
    recently_completed = []
    completed_nofigs = []
    all_completed_xml = []  # [(anime_xml, last_updated_ts)]
    all_mal_ids = []
    anime_list_xml = ElementTree.fromstring(response.content)

    anime_list_error = anime_list_xml.find('error')
    if anime_list_error != None:
        raise AnimeListError(anime_list_error.text)

    for anime in anime_list_xml.findall('anime'):
        my_status = anime.find('my_status').text
        if my_status not in INCLUDE_STATUSES:
            continue

        all_mal_ids.append(anime.find('series_animedb_id').text)
        if anime.find('my_status').text == '2':
            all_completed_xml.append((anime, anime.find('my_last_updated').text))

        if anime.find('my_status').text == '1' and len(watching) <= MAX_WATCHING_COUNT:
            series, figure_count = get_series_obj(anime)
            if figure_count:
                watching.append(series)
            else:
                watching_nofigs.append(series)

    all_completed_xml.sort(key=lambda (_, last_updated_ts): last_updated_ts, reverse=True)
    for anime, _ in all_completed_xml[:RECENTLY_COMPLETED_COUNT]:
        series, figure_count = get_series_obj(anime)
        if figure_count:
            recently_completed.append(series)
        else:
            completed_nofigs.append(series)

    return {
        'watching': watching,
        'recently_completed': recently_completed,
        'watching_nofigs': watching_nofigs,
        'completed_nofigs': completed_nofigs,
        'all_mal_ids': all_mal_ids,
    }


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
    return anime_series, len(figures)


def user_lookup(request):
    mal_lookup = request.POST.get('malLookup', '')
    if 'myanimelist.net' in mal_lookup:
        # parse the MAL username from the URL
        mal_lookup = mal_lookup.split('/')[-1]

    if mal_lookup:
        return HttpResponseRedirect('/user/%s' % mal_lookup)

    return HttpResponseRedirect('/')


def user(request, user_id):
    logger.info('Looking up anime list for %s' % user_id)
    try:
        series_objs = get_anime_list(user_id)
    except AnimeListError as e:
        messages.error(request, 'Error looking up %s: %s' % (user_id, e.msg))
        return HttpResponseRedirect('/')
    response_fields = {
        'mal_name': user_id,
        'recent_figures': get_recent_figures(series_objs['all_mal_ids']),
    }
    response_fields.update(series_objs)
    return render(request, 'anime/user_2.html', response_fields)
