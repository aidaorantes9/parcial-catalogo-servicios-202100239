"""Historial de ejecuciones del importador y sus observaciones: solo lectura y solo ADMIN.

Ninguna vista modifica datos (solo GET/HEAD). La importación se ejecuta por comando
(`importar_catalogo`, `scripts/importar.sh`).
"""

from django.db.models import Count
from django.views.generic import DetailView, ListView

from cuentas.permisos import AdminRequeridoMixin
from importacion.models import Ejecucion


class SoloLecturaMixin(AdminRequeridoMixin):
    http_method_names = ["get", "head"]


class EjecucionListaView(SoloLecturaMixin, ListView):
    template_name = "importacion/ejecucion_lista.html"
    context_object_name = "ejecuciones"
    paginate_by = 20

    def get_queryset(self):
        return Ejecucion.objects.annotate(nuevas=Count("observaciones", distinct=True)).order_by(
            "-iniciada_en", "-pk"
        )


class EjecucionDetalleView(SoloLecturaMixin, DetailView):
    template_name = "importacion/ejecucion_detalle.html"
    context_object_name = "ejecucion"
    model = Ejecucion

    def get_context_data(self, **kwargs):
        observaciones = self.object.observaciones_emitidas.select_related(
            "servicio_nivel1", "servicio_nivel2"
        ).order_by("tipo", "codigo_afectado", "pk")
        conteos = self.object.detalle_conteos or {}
        entidades = [
            (etiqueta, conteos[clave])
            for clave, etiqueta in (
                ("clase", "Clases de servicio"),
                ("criticidad", "Criticidades"),
                ("tipo", "Tipos de servicio"),
                ("nivel1", "Servicios de nivel 1"),
                ("nivel2", "Servicios de nivel 2"),
            )
            if clave in conteos
        ]
        return super().get_context_data(
            observaciones=observaciones,
            entidades=entidades,
            filas=conteos.get("filas", {}),
            por_tipo=conteos.get("observaciones", {}).get("por_tipo", {}),
            **kwargs,
        )
