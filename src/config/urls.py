from django.urls import include, path

from config import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("salud/", views.salud, name="salud"),
    path("", include("cuentas.urls")),
    path("organizacion/", include("organizacion.urls")),
    path("catalogo/", include("catalogo.urls")),
]
