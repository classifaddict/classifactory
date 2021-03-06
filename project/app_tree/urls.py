from django.conf.urls import url
import views

urlpatterns = [
    url(r'^elements/$', views.element_list),
    url(r'^elements/(?P<pk>[0-9]+)/$', views.element_detail),
    url(r'^elements/fancy/$', views.home, name='home'),
    url(r'^elements/fancy/(?P<mode>(table|tree))/$', views.mode, name='mode'),
    url(r'^elements/fancy/roots/$', views.element_fancy_roots, name='roots'),
    url(r'^elements/fancy/ancestors/(?P<pk>[0-9]+)/$', views.element_fancy_ancestors, name='ancestors'),
    url(r'^elements/fancy/search/(?P<query>[0-9A-Za-z@=_:! ]+)/$', views.element_fancy_search, name='search'),
    url(r'^elements/fancy/(?P<mode>(table|tree))/(?P<pk>[0-9]+)/$', views.element_fancy_children, name='children'),
    #url(r'^elements/fancy/diffs/(?P<doctype_name>[a-z_]+)/(?P<dataset_name>[0-9]{1,8})/$', views.diffs, name='diffs'),
]