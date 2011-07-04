from django.conf.urls.defaults import patterns, include, url

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
    url(r'^site_items_list$', 'Dashboard.views.site_items_list'),
    url(r'^show_item$', 'Dashboard.views.show_item'),
    url(r'^update_category_groups$', 'Dashboard.views.update_category_groups'),
    url(r'^ajax/update_category_groups$', 'Dashboard.views.ajax_update_category_groups'),
    url(r'^s/jquery-1.6.1.min.js$', 'Dashboard.views.serve_jquery')
)
