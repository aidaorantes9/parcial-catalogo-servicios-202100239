from django.urls import path

from catalogo import views
from catalogo.models import ServicioNivel1, ServicioNivel2

app_name = "catalogo"

# (modelo, segmento de URL, vista de listado, vista de detalle)
ENTIDADES = [
    (ServicioNivel2, "servicios", views.Nivel2ListaView, views.Nivel2DetalleView),
    (ServicioNivel1, "nivel1", views.Nivel1ListaView, views.Nivel1DetalleView),
    *[
        (modelo, segmento, views.ValorListaView, views.ValorDetalleView)
        for modelo, segmento in views.VALORES.items()
    ],
]

urlpatterns = [path("", views.IndiceView.as_view(), name="indice")]
for modelo, segmento, lista, detalle in ENTIDADES:
    nombre = modelo._meta.model_name
    urlpatterns += [
        path(f"{segmento}/", lista.as_view(modelo=modelo), name=f"{nombre}_lista"),
        path(f"{segmento}/nuevo/", views.CrearView.as_view(modelo=modelo), name=f"{nombre}_crear"),
        path(f"{segmento}/<int:pk>/", detalle.as_view(modelo=modelo), name=f"{nombre}_detalle"),
        path(
            f"{segmento}/<int:pk>/editar/",
            views.EditarView.as_view(modelo=modelo),
            name=f"{nombre}_editar",
        ),
        path(
            f"{segmento}/<int:pk>/desactivar/",
            views.CambiarEstadoView.as_view(modelo=modelo, activar=False, vista_detalle=detalle),
            name=f"{nombre}_desactivar",
        ),
        path(
            f"{segmento}/<int:pk>/reactivar/",
            views.CambiarEstadoView.as_view(modelo=modelo, activar=True, vista_detalle=detalle),
            name=f"{nombre}_reactivar",
        ),
    ]
