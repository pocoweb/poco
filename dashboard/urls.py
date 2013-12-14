from django.conf.urls.defaults import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'dashboard.views.home', name='home'),
    # url(r'^dashboard/', include('dashboard.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'dashboard.views.index', name='index'),
    url(r'^login$', 'dashboard.views.login'),
    url(r'^logout$', 'dashboard.views.logout'),
    url(r'^dashboard/$', 'dashboard.views.dashboard'),
    url(r'^apply$', 'dashboard.views.apply'),
    url(r'^site_items_list$', 'dashboard.views.site_items_list'),
    url(r'^show_item$', 'dashboard.views.show_item'),
    url(r'^update_category_groups$', 'dashboard.views.update_category_groups'),
    url(r'^report/(?P<api_key>.+)/$', 'dashboard.views.report'),
    url(r'^items/(?P<api_key>.+)/$', 'dashboard.views.items'),
    url(r'^edm/(?P<api_key>.+)/$', 'dashboard.views.edm'),
    url(r'^edm_preview/(?P<api_key>.+)/(?P<emailing_user_id>.+)/$', 'dashboard.views.edm_preview'),
    url(r'^edm_send/(?P<api_key>.+)/(?P<emailing_user_id>.+)/$', 'dashboard.views.edm_send'),
    url(r'^user/$', 'dashboard.views.user'),
    url(r'^ajax/update_category_groups$', 'dashboard.views.ajax_update_category_groups'),
    url(r'^ajax/update_category_groups2$', 'dashboard.views.ajax_update_category_groups2'),
    url(r'^ajax/get_site_statistics$', 'dashboard.views.ajax_get_site_statistics'),
    url(r'^ajax/toggle_black_list$', 'dashboard.views.ajax_toggle_black_list'),
    url(r'^ajax/toggle_black_list2$', 'dashboard.views.ajax_toggle_black_list2'),
    url(r'^ajax/get_black_list$', 'dashboard.views.ajax_get_black_list'),
    url(r'^ajax/report$', 'dashboard.views.ajax_report'),
    url(r'^ajax/categroup$', 'dashboard.views.ajax_categroup'),
    url(r'^ajax/change_password$', 'dashboard.views.ajax_change_password'),
    url(r'^ajax/items/(?P<api_key>.+)/id/(?P<item_id>.+)$', 'dashboard.views.ajax_item'),
    url(r'^ajax/items/(?P<api_key>.+)/$', 'dashboard.views.ajax_items'),
    url(r'^ajax/recs/(?P<api_key>.+)/id/(?P<item_id>.+)/(?P<rec_type>.+)$', 'dashboard.views.ajax_recs'),
)

urlpatterns += staticfiles_urlpatterns()
