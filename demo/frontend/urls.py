from django.conf.urls.defaults import *
from frontend import views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

import os
urlpatterns = patterns('',
    # Example:
    # (r'^frontend/', include('frontend.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
    (r'^$', views.index),
    (r'^google_it$', views.google_it),
    #(r'^category$', views.category),
    (r'^search$', views.search),
    (r'^item_details$', views.item_details),
    (r'^api/rate$', views.api_rate),
    (r'clean_all_ratings$', views.clean_all_ratings),
    (r'^login$', views.login),
    (r'^logout$', views.logout),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', 
      {'document_root': os.path.join(os.path.dirname(__file__), 'static').replace('\\','/')}),
)
