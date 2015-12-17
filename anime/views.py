import logging

from django.contrib import messages
from django.http.response import HttpResponseRedirect
from django.shortcuts import render

from anime_figures import AnimeListError, get_anime_list, get_recent_figures

logger = logging.getLogger(__name__)


def index(request):
    return render(request, 'anime/index.html', {})


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
