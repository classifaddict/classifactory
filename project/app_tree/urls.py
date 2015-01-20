from django.conf.urls import url
import views

urlpatterns = [
    url(r'^elements/$', views.element_list),
    url(r'^elements/(?P<pk>[0-9]+)/$', views.element_detail),
    url(r'^elements/fancy/$', views.home, name='home'),
    url(r'^elements/fancy/roots/$', views.element_fancy_roots, name='roots'),
    url(r'^elements/fancy/ancestors/(?P<pk>[0-9]+)/$', views.element_fancy_ancestors, name='ancestors'),
    url(r'^elements/fancy/search/(?P<query>[0-9A-Za-z@= ]+)/$', views.element_fancy_search, name='search'),
    url(r'^elements/fancy/(?P<pk>[0-9]+)/$', views.element_fancy_children, name='children'),
]