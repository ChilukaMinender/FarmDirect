from django.urls import path
from . import views

urlpatterns = [
    # Customer notifications
    path(
        "notifications/",
        views.customer_notifications,
        name="customer_notifications",
    ),
    path(
        "notifications/status/",
        views.notification_status,
        name="notification_status",
    ),
    path(
        "notifications/<int:pk>/read/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),

    # Checkout
    path(
        "checkout/",
        views.checkout,
        name="checkout",
    ),

    # Customer orders
    path(
        "my-orders/",
        views.my_orders,
        name="my_orders",
    ),
    path(
        "my-orders/<int:pk>/",
        views.order_detail,
        name="order_detail",
    ),
    path(
        "my-orders/<int:pk>/cancel/",
        views.cancel_order,
        name="cancel_order",
    ),

    # Farmer orders
    path(
        "farmer/orders/",
        views.farmer_orders,
        name="farmer_orders",
    ),
    path(
        "farmer/orders/<int:pk>/status/",
        views.update_order_status,
        name="update_order_status",
    ),
    path(
        "farmer/orders/<int:pk>/",
        views.farmer_order_detail,
        name="farmer_order_detail",
    ),
]