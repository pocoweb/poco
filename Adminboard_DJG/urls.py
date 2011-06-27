from django.conf.urls.defaults import patterns, include, url
import os.path


# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

#raise os.path.join(os.path.dirname(__file__)

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'Dashboard.views.home', name='home'),
    # url(r'^Dashboard/', include('Dashboard.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'Adminboard_DJG.views.index'),
    url(r'^ajax/calcAsap$', 'Adminboard_DJG.views.ajax_calc_asap'),
    url(r'^ajax/loadData$', 'Adminboard_DJG.views.ajax_load_data'),
    url(r'add_site', 'Adminboard_DJG.views.add_site'),
    url(r'edit_site','Adminboard_DJG.views.edit_site'),
    url(r'^login$', 'Adminboard_DJG.views.login'),
    url(r'^logout$', 'Adminboard_DJG.views.logout'),
    url(r'^s/jquery-1.6.1.min.js$', 'Adminboard_DJG.views.serve_jquery'),
    #(r'^static/(?P<path>.*)$', 'django.views.static.serve',
    #  {'document_root': os.path.join(os.path.dirname(__file__), 'static').replace('\\','/')})
    )
