from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$',
        views.category_list, name='category-list'),
    url(r'^(?P<root_pk>[0-9]+)/$',
        views.category_list, name='category-list'),
    url(r'^paginate/$',
        views.paginate_category, name='category-paginate'),
    url(r'^paginate/(?P<root_pk>[0-9]+)/$',
        views.paginate_category, name='category-paginate'),
    url(r'^search/category/$',
        views.category_search, name='category-search'),
    url(r'^search/paginate/(?P<root_pk>[0-9]+)/$',
        views.category_search, name='category-search'),

    url(r'^add/$',
        views.category_create, name='category-add'),
    url(r'^(?P<root_pk>[0-9]+)/add/$',
        views.category_create, name='category-add'),
    url(r'^(?P<root_pk>[0-9]+)/edit/$',
        views.category_edit, name='category-edit'),
    url(r'^(?P<pk>[0-9]+)/delete/$',
        views.category_delete, name='category-delete'),
    url(r'search/$',
        views.search_category, name='search-category')
]
