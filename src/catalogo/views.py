"""Mantenimiento del catálogo: clase, criticidad, tipo, servicios de nivel 1 y de nivel 2.

Lectura (listados, detalles y fichas): ADMIN y CONSULTA. Escritura (crear, editar, desactivar,
reactivar): solo ADMIN, validado en el servidor. No hay borrado físico: ninguna vista atiende
DELETE. Cada vista recibe el modelo en `as_view(modelo=...)` (ver urls.py).
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from catalogo.forms import ServicioNivel1Form, ServicioNivel2Form, formularios_valor
from catalogo.models import (
    ACTIVO_EXCEL_RECONOCIDOS,
    ClaseServicio,
    Criticidad,
    EstadoRevision,
    ServicioNivel1,
    ServicioNivel2,
    TipoServicio,
)
from cuentas.permisos import AdminRequeridoMixin, LecturaRequeridaMixin
from importacion.models import Observacion
from organizacion.models import Seccion
from organizacion.views import enlaces

# Catálogos de atributos y segmento de URL.
VALORES = {ClaseServicio: "clases", Criticidad: "criticidades", TipoServicio: "tipos"}

ACCIONES = ("lista", "detalle", "crear", "editar", "desactivar", "reactivar")
ESTADOS = {"activos": True, "inactivos": False}
# Valor de los filtros por FK que selecciona los registros sin dato (NULL, D6).
SIN_DATO = "sin"
FILTROS_ACTIVO_EXCEL = {
    "S": Q(activo_excel="S"),
    "N": Q(activo_excel="N"),
    "desconocido": Q(activo_excel__isnull=True),
    "otros": Q(activo_excel__isnull=False) & ~Q(activo_excel__in=ACTIVO_EXCEL_RECONOCIDOS),
}
# Parámetro GET → campo FK del servicio de nivel 2.
FILTROS_FK = {
    "nivel1": "nivel1",
    "clase": "clase",
    "criticidad": "criticidad",
    "tipo": "tipo",
    "seccion": "seccion_responsable",
}
# Columnas del Excel de los atributos con catálogo, para mostrar el original no reconocido.
COLUMNAS_CATALOGO = {"clase": "F", "criticidad": "G", "tipo": "H"}


def url_de(modelo, accion):
    """Nombre de URL de una acción: «catalogo:servicionivel2_detalle»."""
    return f"catalogo:{modelo._meta.model_name}_{accion}"


def filtrar_por_estado(consulta, estado):
    return consulta.filter(activo=ESTADOS[estado]) if estado in ESTADOS else consulta


def parametros_sin_pagina(request):
    filtros = request.GET.copy()
    filtros.pop("page", None)
    return filtros.urlencode()


class CatalogoMixin:
    modelo = None
    template_name_sufijo = None

    def get_queryset(self):
        return self.modelo.objects.all()

    def get_template_names(self):
        return [f"catalogo/{self.template_name_sufijo}.html"]

    def get_context_data(self, **kwargs):
        meta = self.modelo._meta
        return super().get_context_data(
            entidad=meta.verbose_name,
            entidad_plural=meta.verbose_name_plural,
            urls={a: url_de(self.modelo, a) for a in ACCIONES},
            **kwargs,
        )


class IndiceView(LecturaRequeridaMixin, TemplateView):
    """Punto de entrada del catálogo con los conteos de cada entidad."""

    template_name = "catalogo/indice.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(conteos=conteos_catalogo(), **kwargs)


def conteos_catalogo():
    """(nombre, activos, total, URL de listado) de cada entidad del catálogo."""
    modelos = [ServicioNivel1, ServicioNivel2, *VALORES]
    return [
        (
            m._meta.verbose_name_plural.capitalize(),
            m.objects.filter(activo=True).count(),
            m.objects.count(),
            url_de(m, "lista"),
        )
        for m in modelos
    ]


# ---------------------------------------------------------------- catálogos de atributos


class ValorListaView(LecturaRequeridaMixin, CatalogoMixin, ListView):
    template_name_sufijo = "valor_lista"
    context_object_name = "registros"
    paginate_by = 20

    def get_queryset(self):
        consulta = self.modelo.objects.annotate(
            servicios_activos=Count("servicios", filter=Q(servicios__activo=True))
        ).order_by("orden", "codigo")
        self.busqueda = self.request.GET.get("q", "").strip()
        self.estado = self.request.GET.get("estado", "")
        if self.busqueda:
            consulta = consulta.filter(
                Q(codigo__icontains=self.busqueda)
                | Q(etiqueta_mostrada__icontains=self.busqueda)
                | Q(etiqueta_original__icontains=self.busqueda)
            )
        return filtrar_por_estado(consulta, self.estado)

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            busqueda=self.busqueda,
            estado=self.estado,
            filtros=parametros_sin_pagina(self.request),
            **kwargs,
        )


class ValorDetalleView(LecturaRequeridaMixin, CatalogoMixin, DetailView):
    template_name_sufijo = "valor_detalle"
    context_object_name = "registro"

    def get_context_data(self, **kwargs):
        servicios = self.object.servicios.select_related("nivel1").order_by("codigo")
        return super().get_context_data(servicios=servicios, **kwargs)


class FormularioMixin(AdminRequeridoMixin, CatalogoMixin):
    template_name_sufijo = "formulario"

    def get_success_url(self):
        return reverse(url_de(self.modelo, "detalle"), args=[self.object.pk])


class CrearView(FormularioMixin, CreateView):
    def get_form_class(self):
        if self.modelo in VALORES:
            return formularios_valor(self.modelo)[0]
        return ServicioNivel1Form if self.modelo is ServicioNivel1 else ServicioNivel2Form

    def get_initial(self):
        # «Nuevo servicio de nivel 2» desde la ficha del nivel 1 (?nivel1=<id>).
        nivel1 = self.request.GET.get("nivel1", "")
        if self.modelo is ServicioNivel2 and nivel1.isdigit():
            return {"nivel1": nivel1}
        return {}

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            titulo=f"Nuevo registro de {self.modelo._meta.verbose_name}", **kwargs
        )

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, f"«{self.object}» creado.")
        return respuesta


class EditarView(FormularioMixin, UpdateView):
    def get_form_class(self):
        if self.modelo in VALORES:
            return formularios_valor(self.modelo)[1]
        return ServicioNivel1Form if self.modelo is ServicioNivel1 else ServicioNivel2Form

    def get_context_data(self, **kwargs):
        return super().get_context_data(titulo=f"Editar {self.modelo._meta.verbose_name}", **kwargs)

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, f"«{self.object}» actualizado.")
        return respuesta


class CambiarEstadoView(AdminRequeridoMixin, CatalogoMixin, View):
    """Baja lógica o reactivación (solo POST).

    D1: desactivar con dependientes activos (N2 de un N1, servicios que usan un valor de
    catálogo) se rechaza y se muestra la lista en el detalle. Reactivar un N2 con referencias
    inactivas también se rechaza (validación de `clean()`).
    """

    http_method_names = ["post"]
    activar = False
    vista_detalle = None

    def post(self, request, pk):
        registro = get_object_or_404(self.get_queryset(), pk=pk)
        detalle = reverse(url_de(self.modelo, "detalle"), args=[pk])
        if registro.activo == self.activar:
            messages.info(request, f"«{registro}» ya estaba en ese estado.")
            return redirect(detalle)

        if not self.activar:
            dependientes = registro.dependientes_activos()
            if dependientes:
                messages.error(
                    request,
                    f"No se puede desactivar «{registro}»: tiene {len(dependientes)} "
                    "dependiente(s) activo(s). Desactívelos o reasígnelos primero.",
                )
                return self._detalle_con_bloqueo(registro, dependientes)

        registro.activo = self.activar
        try:
            registro.full_clean()
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            registro.save(update_fields=["activo", "actualizado_en"])
            accion = "reactivado" if self.activar else "desactivado"
            messages.success(request, f"«{registro}» {accion}.")
        return redirect(detalle)

    def _detalle_con_bloqueo(self, registro, dependientes):
        vista = self.vista_detalle(
            modelo=self.modelo, request=self.request, kwargs={"pk": registro.pk}
        )
        vista.object = registro
        contexto = vista.get_context_data(dependientes_bloqueo=enlaces(dependientes))
        return render(self.request, vista.get_template_names(), contexto)


# ---------------------------------------------------------------- servicios de nivel 1


class Nivel1ListaView(LecturaRequeridaMixin, CatalogoMixin, ListView):
    template_name_sufijo = "nivel1_lista"
    context_object_name = "registros"
    paginate_by = 20

    def get_queryset(self):
        consulta = ServicioNivel1.objects.annotate(
            total_n2=Count("servicios_nivel2"),
            activos_n2=Count("servicios_nivel2", filter=Q(servicios_nivel2__activo=True)),
        ).order_by("codigo", "pk")
        self.busqueda = self.request.GET.get("q", "").strip()
        self.estado = self.request.GET.get("estado", "")
        self.revision = self.request.GET.get("revision", "")
        if self.busqueda:
            consulta = consulta.filter(
                Q(codigo__icontains=self.busqueda) | Q(nombre__icontains=self.busqueda)
            )
        if self.revision in EstadoRevision.values:
            consulta = consulta.filter(estado_revision=self.revision)
        return filtrar_por_estado(consulta, self.estado)

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            busqueda=self.busqueda,
            estado=self.estado,
            revision=self.revision,
            estados_revision=EstadoRevision.choices,
            filtros=parametros_sin_pagina(self.request),
            **kwargs,
        )


def trazabilidad(servicio, campo):
    """Origen vigente y observaciones de importación de un servicio (vacíos si se creó en la
    aplicación). Solo se muestran las observaciones de la última ejecución que lo procesó, para no
    repetir las de importaciones anteriores."""
    origen = getattr(servicio, "origen", None)
    observaciones = Observacion.objects.filter(**{campo: servicio}).select_related("ejecucion")
    if origen is not None:
        observaciones = observaciones.filter(ejecucion=origen.ultima_ejecucion)
    valores = []
    if origen is not None:
        valores = [
            (columna, dato.get("celda", ""), dato.get("valor"))
            for columna, dato in sorted(origen.valores_originales.items())
        ]
    return {"origen": origen, "valores_originales": valores, "observaciones": observaciones}


class Nivel1DetalleView(LecturaRequeridaMixin, CatalogoMixin, DetailView):
    template_name_sufijo = "nivel1_detalle"
    context_object_name = "registro"

    def get_context_data(self, **kwargs):
        servicios = self.object.servicios_nivel2.select_related(
            "clase", "criticidad", "tipo", "seccion_responsable"
        ).order_by("codigo")
        return super().get_context_data(
            servicios=servicios,
            **trazabilidad(self.object, "servicio_nivel1"),
            **kwargs,
        )


# ---------------------------------------------------------------- servicios de nivel 2


class Nivel2ListaView(LecturaRequeridaMixin, CatalogoMixin, ListView):
    """Búsqueda por código o nombre y filtros combinables (modelo-datos.md §3.3, «Filtros del
    listado»). `activo` y `activo_excel` se filtran por separado (D8). La paginación conserva los
    filtros."""

    template_name_sufijo = "nivel2_lista"
    context_object_name = "registros"
    paginate_by = 20

    def get_queryset(self):
        consulta = ServicioNivel2.objects.select_related(
            "nivel1", "clase", "criticidad", "tipo", "seccion_responsable", "usuario_responsable"
        ).order_by("codigo", "pk")
        parametros = self.request.GET
        self.criterios = {
            "q": parametros.get("q", "").strip(),
            # Por defecto solo registros activos; «todos» quita la condición.
            "estado": parametros.get("estado", "activos"),
            "activo_excel": parametros.get("activo_excel", ""),
            "revision": parametros.get("revision", ""),
            **{p: parametros.get(p, "") for p in FILTROS_FK},
        }
        criterios = self.criterios
        if criterios["q"]:
            consulta = consulta.filter(
                Q(codigo__icontains=criterios["q"]) | Q(nombre__icontains=criterios["q"])
            )
        if criterios["estado"] not in (*ESTADOS, "todos"):
            criterios["estado"] = "activos"
        consulta = filtrar_por_estado(consulta, criterios["estado"])
        if criterios["activo_excel"] in FILTROS_ACTIVO_EXCEL:
            consulta = consulta.filter(FILTROS_ACTIVO_EXCEL[criterios["activo_excel"]])
        if criterios["revision"] in EstadoRevision.values:
            consulta = consulta.filter(estado_revision=criterios["revision"])
        for parametro, campo in FILTROS_FK.items():
            valor = criterios[parametro]
            if valor == SIN_DATO:
                consulta = consulta.filter(**{f"{campo}__isnull": True})
            elif valor.isdigit():
                consulta = consulta.filter(**{f"{campo}_id": int(valor)})
        return consulta

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            criterios=self.criterios,
            opciones={
                "nivel1": ServicioNivel1.objects.order_by("codigo"),
                "clase": ClaseServicio.objects.all(),
                "criticidad": Criticidad.objects.all(),
                "tipo": TipoServicio.objects.all(),
                "seccion": Seccion.con_jerarquia().order_by(
                    "departamento__area__empresa__codigo", "codigo"
                ),
            },
            estados_revision=EstadoRevision.choices,
            sin_dato=SIN_DATO,
            filtros=parametros_sin_pagina(self.request),
            **kwargs,
        )


class Nivel2DetalleView(LecturaRequeridaMixin, CatalogoMixin, DetailView):
    """Ficha: todos los atributos, nivel 1, responsables, estado de revisión, valores originales y
    observaciones de importación. NULL se muestra como «Sin dato» o «Desconocido», nunca como 0."""

    template_name_sufijo = "nivel2_detalle"
    context_object_name = "servicio"

    def get_queryset(self):
        return ServicioNivel2.objects.select_related(
            "nivel1",
            "clase",
            "criticidad",
            "tipo",
            "seccion_responsable__departamento__area__empresa",
            "usuario_responsable__puesto__seccion",
        )

    def get_context_data(self, **kwargs):
        servicio = self.object
        datos = trazabilidad(servicio, "servicio_nivel2")
        originales = {}
        if datos["origen"] is not None:
            # Atributo sin valor reconocido: se muestra el texto original del Excel (§3.3).
            for campo, columna in COLUMNAS_CATALOGO.items():
                valor = datos["origen"].valores_originales.get(columna, {}).get("valor")
                if getattr(servicio, f"{campo}_id") is None and valor not in (None, ""):
                    originales[campo] = valor
        seccion = servicio.seccion_responsable
        return super().get_context_data(
            ruta_seccion=enlaces([*seccion.ancestros(), seccion]) if seccion else [],
            originales_no_reconocidos=originales,
            **datos,
            **kwargs,
        )
