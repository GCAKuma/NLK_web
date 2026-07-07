from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("", views.order_list, name="list"),
    path("<str:order_number>/", views.order_detail, name="detail"),
    path("<str:order_number>/confirmation/", views.order_confirmation, name="confirmation"),
    path("<str:order_number>/upload-slip/", views.upload_slip, name="upload_slip"),
]
