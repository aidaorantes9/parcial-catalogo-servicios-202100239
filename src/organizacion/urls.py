from django.urls import path

from organizacion import views

app_name = "organizacion"

urlpatterns = []
for modelo, segmento in views.ENTIDADES.items():
    nombre = modelo._meta.model_name
    urlpatterns += [
        path(f"{segmento}/", views.UnidadListaView.as_view(modelo=modelo), name=f"{nombre}_lista"),
        path(
            f"{segmento}/nuevo/",
            views.UnidadCrearView.as_view(modelo=modelo),
            name=f"{nombre}_crear",
        ),
        path(
            f"{segmento}/<int:pk>/",
            views.UnidadDetalleView.as_view(modelo=modelo),
            name=f"{nombre}_detalle",
        ),
        path(
            f"{segmento}/<int:pk>/editar/",
            views.UnidadEditarView.as_view(modelo=modelo),
            name=f"{nombre}_editar",
        ),
        path(
            f"{segmento}/<int:pk>/desactivar/",
            views.UnidadCambiarEstadoView.as_view(modelo=modelo, activar=False),
            name=f"{nombre}_desactivar",
        ),
        path(
            f"{segmento}/<int:pk>/reactivar/",
            views.UnidadCambiarEstadoView.as_view(modelo=modelo, activar=True),
            name=f"{nombre}_reactivar",
        ),
    ]
