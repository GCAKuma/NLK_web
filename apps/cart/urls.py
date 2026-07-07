from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="detail"),
    path("add/", views.add_to_cart, name="add"),
    path("item/<int:item_id>/update/", views.update_item, name="update"),
    path("item/<int:item_id>/remove/", views.remove_item, name="remove"),
]
