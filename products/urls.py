from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("farmer/dashboard/", views.farmer_dashboard, name="farmer_dashboard"),
    path("farmer/products/add/", views.add_product, name="add_product"),
    path("farmer/products/<int:pk>/edit/", views.edit_product, name="edit_product"),
    path("farmer/products/<int:pk>/delete/", views.delete_product, name="delete_product"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.cart_view, name="cart"),

    # Cart quantity update and item removal
    path("cart/update/<int:pk>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:pk>/", views.remove_from_cart, name="remove_from_cart"),
]
