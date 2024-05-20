from django.urls import path, include
from . import views
from rest_framework import routers
from rest_framework_nested import routers

router = routers.DefaultRouter()
router.register('cart', views.ApiCart, basename='cart')
router.register('products', views.ApiProducts, basename='products')
router.register('order', views.ApiOrder, basename='order')

product_router = routers.NestedDefaultRouter(router, 'products', lookup='products')
product_router.register('reviews', views.ApiReview, basename='product-reviews')

cart_router = routers.NestedDefaultRouter(router, 'cart', lookup='cart')
cart_router.register('items', views.ApiCartItem, basename='cart-items')

order_router = routers.NestedDefaultRouter(router, 'order', lookup='order')
order_router.register('items', views.ApiOrderItem, basename='order-items')

urlpatterns = [
    path("", include(router.urls)),
    path("", include(product_router.urls)),
    path("", include(cart_router.urls)),
    path("", include(order_router.urls)),
]
