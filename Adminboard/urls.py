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
    url(r'^$', 'Adminboard.views.index'),
    url(r'^ajax/calcAsap$', 'Adminboard.views.ajax_calc_asap'),
    url(r'^ajax/loadData$', 'Adminboard.views.ajax_load_data'),
    url(r'^add_site$', 'Adminboard.views.add_site'),
    url(r'^edit_site$','Adminboard.views.edit_site'),
    url(r'^add_user$', 'Adminboard.views.add_user'),
    url(r'^edit_user$', 'Adminboard.views.edit_user'),
    url(r'^user_list$', 'Adminboard.views.user_list'),
    url(r'^login$', 'Adminboard.views.login'),
    url(r'^logout$', 'Adminboard.views.logout'),
    url(r'^s/jquery-1.6.1.min.js$', 'Adminboard.views.serve_jquery'),
    #(r'^static/(?P<path>.*)$', 'django.views.static.serve',
    #  {'document_root': os.path.join(os.path.dirname(__file__), 'static').replace('\\','/')})
    )
