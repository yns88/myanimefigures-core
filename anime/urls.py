from django.conf.urls import url
from django.views.generic.base import RedirectView

from . import views

urlpatterns = [
    url(r'^favicon\.ico$', RedirectView.as_view(url='/static/favicon/favicon.ico')),
    url(r'^$', views.index, name='index'),
    url(r'^user/?$', views.user_lookup, name='user_lookup'),
    url(r'^user/(?P<user_id>.+)/?$', views.user, name='user'),
]
