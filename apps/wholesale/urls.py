from django.urls import path

from . import views

app_name = "wholesale"

urlpatterns = [
    path("", views.quotation, name="quotation"),
]
