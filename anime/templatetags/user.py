from django import template

register = template.Library()


@register.inclusion_tag('anime_gridobj.html')
def show_anime(anime):
    return {'anime': anime}


@register.inclusion_tag('figure_gridobj.html')
def show_figure(figure):
    return {'figure': figure}


@register.inclusion_tag('content_rows.html')
def show_content_rows(series_list, nofigs_list):
    return {'series_list': series_list, 'nofigs_list': nofigs_list}
