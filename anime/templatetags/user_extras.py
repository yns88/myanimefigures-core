from django import template

register = template.Library()


@register.inclusion_tag('anime/anime_gridobj.html')
def show_anime(anime, show_text=True):
    return {'anime_obj': anime, 'show_text': show_text}


@register.inclusion_tag('anime/figure_gridobj.html')
def show_figure(figure):
    return {'figure': figure}


@register.inclusion_tag('anime/content_rows.html')
def show_content_rows(series_list, nofigs_list, series_id_to_figures):
    return {
        'series_list': series_list,
        'nofigs_list': nofigs_list,
        'series_id_to_figures': series_id_to_figures,
    }


@register.inclusion_tag('anime/favicon.html')
def favicon():
    return {}


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
