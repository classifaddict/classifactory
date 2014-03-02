from django.conf.urls import patterns, url
from app_scheme import views

urlpatterns = patterns('',
    url(r'^$', views.home, name='home'),
    url(r'^topconcepts/$', views.topconcepts, name='topconcepts'),
    url(r'^concept/(?P<pk>[0-9]+)/$', views.concept, name='concept'),
)
