from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("shop/", views.product_list, name="shop"),
    path("tools/calculator-finder/", views.calculator_finder, name="calculator_finder"),
    path("tools/compare/", views.compare_calculators, name="compare"),
    path("category/<slug:category_slug>/", views.product_list, name="category"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("product/<slug:slug>/ask/", views.ask_question, name="ask_question"),
]
