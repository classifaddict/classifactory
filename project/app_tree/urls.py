from django.conf.urls import url
import views

urlpatterns = [
    url(r'^elements/$', views.element_list),
    url(r'^elements/(?P<pk>[0-9]+)/$', views.element_detail),
    url(r'^elements/fancy/$', views.home, name='home'),
    url(r'^elements/fancy/roots/$', views.element_fancy_roots, name='roots'),
    url(r'^elements/fancy/(?P<pk>[0-9]+)/$', views.element_fancy_children),
]