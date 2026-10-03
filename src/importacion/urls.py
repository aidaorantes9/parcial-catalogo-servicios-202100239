from django.urls import path

from importacion import views

app_name = "importacion"

urlpatterns = [
    path("ejecuciones/", views.EjecucionListaView.as_view(), name="ejecucion_lista"),
    path("ejecuciones/<int:pk>/", views.EjecucionDetalleView.as_view(), name="ejecucion_detalle"),
]
