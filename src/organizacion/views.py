"""Mantenimiento de Empresa, Área, Departamento, Sección y Puesto con vistas genéricas comunes.

Cada vista recibe el modelo en `as_view(modelo=...)` (ver urls.py). Lectura: ADMIN y CONSULTA.
Escritura (crear, editar, desactivar, reactivar): solo ADMIN, validado en el servidor. No hay
borrado físico: ninguna vista atiende DELETE.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cuentas.permisos import AdminRequeridoMixin, LecturaRequeridaMixin
from organizacion.forms import formulario_para
from organizacion.models import Area, Departamento, Empresa, Puesto, Seccion

# Orden de la jerarquía y segmento de URL de cada entidad.
ENTIDADES = {
    Empresa: "empresas",
    Area: "areas",
    Departamento: "departamentos",
    Seccion: "secciones",
    Puesto: "puestos",
}

ACCIONES = ("lista", "detalle", "crear", "editar", "desactivar", "reactivar")
ESTADOS = {"activos": True, "inactivos": False}


def url_de(modelo, accion):
    """Nombre de URL de una acción: «organizacion:area_detalle»."""
    return f"organizacion:{modelo._meta.model_name}_{accion}"


def enlaces(registros):
    """Pares (registro, URL de su detalle)."""
    return [(r, reverse(url_de(type(r), "detalle"), args=[r.pk])) for r in registros]


def enlaces_usuarios(usuarios):
    """Pares (usuario, URL de su detalle). El detalle de usuarios es solo de ADMIN, así que el
    enlace se agrega en la plantilla únicamente para ese rol."""
    return [(u, reverse("cuentas:usuario_detalle", args=[u.pk])) for u in usuarios]


def modelo_hijo(modelo):
    for candidato in ENTIDADES:
        if candidato.campo_padre and candidato.modelo_padre() is modelo:
            return candidato
    return None


class EntidadMixin:
    modelo = None

    def get_queryset(self):
        return self.modelo.con_jerarquia()

    def get_context_data(self, **kwargs):
        meta = self.modelo._meta
        modelo_padre = self.modelo.modelo_padre()
        return super().get_context_data(
            entidad=meta.verbose_name,
            entidad_plural=meta.verbose_name_plural,
            padre_nombre=modelo_padre._meta.verbose_name if modelo_padre else None,
            urls={a: url_de(self.modelo, a) for a in ACCIONES},
            **kwargs,
        )


class UnidadListaView(LecturaRequeridaMixin, EntidadMixin, ListView):
    """Listado paginado con búsqueda por código o nombre y filtros por estado y por padre."""

    template_name = "organizacion/lista.html"
    context_object_name = "registros"
    paginate_by = 20

    def get_queryset(self):
        consulta = super().get_queryset().order_by("codigo", "pk")
        parametros = self.request.GET
        self.busqueda = parametros.get("q", "").strip()
        self.estado = parametros.get("estado", "")
        self.padre_id = parametros.get("padre", "")
        if self.busqueda:
            consulta = consulta.filter(
                Q(codigo__icontains=self.busqueda) | Q(nombre__icontains=self.busqueda)
            )
        if self.estado in ESTADOS:
            consulta = consulta.filter(activo=ESTADOS[self.estado])
        if self.modelo.campo_padre and self.padre_id.isdigit():
            consulta = consulta.filter(**{f"{self.modelo.campo_padre}_id": self.padre_id})
        return consulta

    def get_context_data(self, **kwargs):
        modelo_padre = self.modelo.modelo_padre()
        filtros = self.request.GET.copy()
        filtros.pop("page", None)
        return super().get_context_data(
            busqueda=self.busqueda,
            estado=self.estado,
            padre_id=self.padre_id,
            padres=modelo_padre.con_jerarquia().order_by("codigo") if modelo_padre else None,
            filtros=filtros.urlencode(),
            **kwargs,
        )


class UnidadDetalleView(LecturaRequeridaMixin, EntidadMixin, DetailView):
    """Detalle con el padre, la ruta completa hasta la empresa y los hijos directos (en Puesto,
    sus usuarios)."""

    template_name = "organizacion/detalle.html"
    context_object_name = "registro"

    def get_context_data(self, **kwargs):
        registro = self.object
        contexto = {"ruta": enlaces(registro.ancestros())}
        hijo = modelo_hijo(self.modelo)
        if hijo:
            contexto.update(
                hijos=enlaces(getattr(registro, self.modelo.relacion_hijos).order_by("codigo")),
                hijo_plural=hijo._meta.verbose_name_plural,
                hijo_singular=hijo._meta.verbose_name,
                hijo_crear=url_de(hijo, "crear"),
            )
        else:
            contexto["usuarios"] = enlaces_usuarios(registro.usuarios.order_by("username"))
        return super().get_context_data(**contexto, **kwargs)


class UnidadFormularioMixin(AdminRequeridoMixin, EntidadMixin):
    template_name = "organizacion/formulario.html"

    def get_form_class(self):
        return formulario_para(self.modelo)

    def get_success_url(self):
        return reverse(url_de(self.modelo, "detalle"), args=[self.object.pk])


class UnidadCrearView(UnidadFormularioMixin, CreateView):
    def get_initial(self):
        # Permite «Nuevo hijo» desde el detalle del padre (?padre=<id>).
        padre = self.request.GET.get("padre", "")
        if self.modelo.campo_padre and padre.isdigit():
            return {self.modelo.campo_padre: padre}
        return {}

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            titulo=f"Nuevo registro de {self.modelo._meta.verbose_name}", **kwargs
        )

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, f"«{self.object}» creado.")
        return respuesta


class UnidadEditarView(UnidadFormularioMixin, UpdateView):
    def get_context_data(self, **kwargs):
        return super().get_context_data(titulo=f"Editar {self.modelo._meta.verbose_name}", **kwargs)

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, f"«{self.object}» actualizado.")
        return respuesta


class UnidadCambiarEstadoView(AdminRequeridoMixin, EntidadMixin, View):
    """Baja lógica o reactivación (solo POST).

    D1: desactivar con dependientes activos se rechaza y se muestra la lista de dependientes en el
    detalle. Reactivar bajo un padre inactivo también se rechaza (validación de `clean()`).
    """

    http_method_names = ["post"]
    activar = False

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
        vista = UnidadDetalleView(
            modelo=self.modelo, request=self.request, kwargs={"pk": registro.pk}
        )
        vista.object = registro
        bloqueos = (
            enlaces(dependientes) if modelo_hijo(self.modelo) else enlaces_usuarios(dependientes)
        )
        contexto = vista.get_context_data(dependientes_bloqueo=bloqueos)
        return render(self.request, vista.template_name, contexto)
