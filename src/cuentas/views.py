from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView

from cuentas.forms import UsuarioCrearForm, UsuarioEditarForm
from cuentas.models import Usuario
from cuentas.permisos import AdminRequeridoMixin


def _usuarios_con_jerarquia():
    return Usuario.objects.select_related("puesto__seccion__departamento__area__empresa")


def perfil(request):
    """Datos propios del usuario en sesión (cualquier rol). No muestra campos de seguridad."""
    return render(request, "cuentas/perfil.html", {"usuario": request.user})


class UsuarioListaView(AdminRequeridoMixin, ListView):
    template_name = "cuentas/usuario_lista.html"
    context_object_name = "usuarios"
    paginate_by = 20

    def get_queryset(self):
        consulta = _usuarios_con_jerarquia().order_by("username")
        self.busqueda = self.request.GET.get("q", "").strip()
        if self.busqueda:
            consulta = consulta.filter(
                Q(username__icontains=self.busqueda)
                | Q(email__icontains=self.busqueda)
                | Q(nombre__icontains=self.busqueda)
            )
        return consulta

    def get_context_data(self, **kwargs):
        return super().get_context_data(busqueda=self.busqueda, **kwargs)


class UsuarioDetalleView(AdminRequeridoMixin, DetailView):
    template_name = "cuentas/usuario_detalle.html"
    context_object_name = "usuario"

    def get_queryset(self):
        return _usuarios_con_jerarquia()


class UsuarioFormularioMixin(AdminRequeridoMixin):
    model = Usuario
    template_name = "cuentas/usuario_formulario.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "usuario_actual": self.request.user}

    def get_success_url(self):
        return reverse("cuentas:usuario_detalle", args=[self.object.pk])


class UsuarioCrearView(UsuarioFormularioMixin, CreateView):
    form_class = UsuarioCrearForm
    extra_context = {"titulo": "Nuevo usuario"}

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, f"Usuario «{self.object.username}» creado.")
        return respuesta


class UsuarioEditarView(UsuarioFormularioMixin, UpdateView):
    form_class = UsuarioEditarForm
    extra_context = {"titulo": "Editar usuario"}

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, f"Usuario «{self.object.username}» actualizado.")
        return respuesta


class UsuarioCambiarEstadoView(AdminRequeridoMixin, View):
    """Baja lógica o reactivación. Solo POST; la sesión del usuario desactivado se cierra en su
    siguiente petición (CerrarSesionInvalidaMiddleware)."""

    http_method_names = ["post"]
    activar = False

    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        if not self.activar and usuario.pk == request.user.pk:
            messages.error(request, "No puede desactivar su propia cuenta.")
        elif usuario.is_active == self.activar:
            messages.info(request, f"El usuario «{usuario.username}» ya estaba en ese estado.")
        else:
            usuario.is_active = self.activar
            try:
                usuario.full_clean()
            except ValidationError as error:
                messages.error(request, " ".join(error.messages))
            else:
                usuario.save(update_fields=["is_active", "actualizado_en"])
                accion = "reactivado" if self.activar else "desactivado"
                messages.success(request, f"Usuario «{usuario.username}» {accion}.")
        return redirect("cuentas:usuario_detalle", pk=usuario.pk)


class UsuarioCambiarPasswordView(AdminRequeridoMixin, FormView):
    """Cambio de contraseña por un administrador. Al cambiar el hash, las sesiones abiertas de ese
    usuario dejan de ser válidas (Django verifica el hash de sesión en cada petición)."""

    form_class = SetPasswordForm
    template_name = "cuentas/usuario_password.html"

    def dispatch(self, request, *args, **kwargs):
        self.usuario = get_object_or_404(Usuario, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.usuario}

    def get_context_data(self, **kwargs):
        return super().get_context_data(usuario=self.usuario, **kwargs)

    def form_valid(self, form):
        form.save()
        if self.usuario.pk == self.request.user.pk:
            update_session_auth_hash(self.request, self.usuario)
        messages.success(self.request, f"Contraseña de «{self.usuario.username}» actualizada.")
        return redirect("cuentas:usuario_detalle", pk=self.usuario.pk)
