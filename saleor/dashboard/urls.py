from django.conf.urls import url, include

from . import views as core_views
from .category.urls import urlpatterns as category_urls
from .customer.urls import urlpatterns as customer_urls
from .drawercash.urls import urlpatterns as drawercash_urls
from .discount.urls import urlpatterns as discount_urls
from .hr.urls import urlpatterns as hr_urls
from .messages.urls import urlpatterns as messages_urls
from .notification.urls import urlpatterns as notification_urls
from .order.urls import urlpatterns as order_urls
from .permgroups.urls import urlpatterns as group_urls
from .product.urls import urlpatterns as product_urls
from .reports.urls import urlpatterns as reports_urls
from .search.urls import urlpatterns as search_urls
from .sites.urls import urlpatterns as site_urls
from .shipping.urls import urlpatterns as shipping_urls
from .supplier.urls import urlpatterns as supplier_urls
from .users.urls import urlpatterns as users_urls




urlpatterns = [
    url(r'^$', core_views.index, name='index'),
    url(r'^categories/', include(category_urls)),
    url(r'^customers/', include(customer_urls)),
    url(r'^discounts/', include(discount_urls)),
    url(r'^drawercash/', include(drawercash_urls)),
    url(r'^hr/', include(hr_urls)),    
    url(r'^orders/', include(order_urls)),
    url(r'^products/', include(product_urls)),
    url(r'^messages/', include(messages_urls)),
    url(r'^notification/',include(notification_urls)),    
    url(r'^perms/', include(group_urls)),
    url(r'^reports/', include(reports_urls)),
    url(r'^search/', include(search_urls)),
    url(r'^settings/', include(site_urls)),
    url(r'^shipping/', include(shipping_urls)),
    url(r'^style-guide/', core_views.styleguide, name='styleguide'),
    url(r'^supplier/', include(supplier_urls)),
    url(r'^users/', include(users_urls)),
    
]
