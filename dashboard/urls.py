from django.conf.urls.defaults import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'Dashboard.views.home', name='home'),
    # url(r'^Dashboard/', include('Dashboard.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'Dashboard.views.index', name='index'),
    url(r'^login$', 'Dashboard.views.login'),
    url(r'^logout$', 'Dashboard.views.logout'),
    url(r'^dashboard/$', 'Dashboard.views.dashboard'),
    url(r'^apply$', 'Dashboard.views.apply'),
    url(r'^site_items_list$', 'Dashboard.views.site_items_list'),
    url(r'^show_item$', 'Dashboard.views.show_item'),
    url(r'^update_category_groups$', 'Dashboard.views.update_category_groups'),
    url(r'^report/(?P<api_key>.+)/$', 'Dashboard.views.report'),
    url(r'^items/(?P<api_key>.+)/$', 'Dashboard.views.items'),
    url(r'^edm/(?P<api_key>.+)/$', 'Dashboard.views.edm'),
    url(r'^edm_preview/(?P<api_key>.+)/(?P<emailing_user_id>.+)/$', 'Dashboard.views.edm_preview'),
    url(r'^edm_send/(?P<api_key>.+)/(?P<emailing_user_id>.+)/$', 'Dashboard.views.edm_send'),
    url(r'^user/$', 'Dashboard.views.user'),
    url(r'^ajax/update_category_groups$', 'Dashboard.views.ajax_update_category_groups'),
    url(r'^ajax/update_category_groups2$', 'Dashboard.views.ajax_update_category_groups2'),
    url(r'^ajax/get_site_statistics$', 'Dashboard.views.ajax_get_site_statistics'),
    url(r'^ajax/toggle_black_list$', 'Dashboard.views.ajax_toggle_black_list'),
    url(r'^ajax/toggle_black_list2$', 'Dashboard.views.ajax_toggle_black_list2'),
    url(r'^ajax/get_black_list$', 'Dashboard.views.ajax_get_black_list'),
    url(r'^ajax/report$', 'Dashboard.views.ajax_report'),
    url(r'^ajax/categroup$', 'Dashboard.views.ajax_categroup'),
    url(r'^ajax/change_password$', 'Dashboard.views.ajax_change_password'),
    url(r'^ajax/items/(?P<api_key>.+)/id/(?P<item_id>.+)$', 'Dashboard.views.ajax_item'),
    url(r'^ajax/items/(?P<api_key>.+)/$', 'Dashboard.views.ajax_items'),
    url(r'^ajax/recs/(?P<api_key>.+)/id/(?P<item_id>.+)/(?P<rec_type>.+)$', 'Dashboard.views.ajax_recs'),
)

urlpatterns += staticfiles_urlpatterns()
