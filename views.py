import datetime
import dateutil.parser
import logging
from xml.etree import ElementTree

from django.shortcuts import render
import requests

from .models import AnimeSeries, Figure

logger = logging.getLogger(__name__)


ANIME_LIST_GET = 'http://myanimelist.net/malappinfo.php?u=%s&status=all&type=anime'
FIGURE_SEARCH = 'http://myfigurecollection.net/api.php?mode=search&keywords=%s'
MAX_ANIMES = 20
MFC_FIGURE_ROOT_ID = '0'
FIGURE_CACHE_DURATION = datetime.timedelta(days=1)
FIGURE_URL = 'http://s1.tsuki-board.net/pics/figure/big/{{ figure.mfc_id }}.jpg'


def index(request):
    return render(request, 'anime/index.html', {})


def sanitize_title(title):
    return title.lstrip(' ').rstrip(' ').rstrip('(TV)')


def get_watching_list(user_id):
    response = requests.get(ANIME_LIST_GET % user_id)
    watching_list = []
    anime_list_xml = ElementTree.fromstring(response.content)
    for anime in anime_list_xml.findall('anime'):
        if anime.find('my_status').text == '1':
            series = AnimeSeries.objects.create_or_update(
                mal_id=anime.find('series_animedb_id').text,
                defaults={
                    'image_url': anime.find('series_image').text,
                    'title': anime.find('series_title').text
                },
            )
            # Make sure figures are up to date
            last_figure_calc = series.last_figure_calc
            cache_cutoff = datetime.datetime.utcnow() - FIGURE_CACHE_DURATION
            if not last_figure_calc or last_figure_calc < cache_cutoff:
                series = recalculate_figures(series)

            watching_list.append(series)
            if len(watching_list) >= MAX_ANIMES:
                break

    logger.info('Found %d watching anime', len(watching_list))
    return watching_list


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
            if release_date_str:
                release_date_str = release_date_str.replace('00', '01')
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
    return anime_series


def user(request, user_id):
    watching_list = get_watching_list(user_id)
    return render(request, 'anime/user.html', {'watching_list': watching_list})
