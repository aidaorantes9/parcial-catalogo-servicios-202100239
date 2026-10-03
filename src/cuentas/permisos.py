"""Autorización por rol, validada en el servidor (ocultar botones no es autorización)."""

from functools import wraps

from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from cuentas.models import Rol


def tiene_rol(usuario, *roles):
    return usuario.is_authenticated and usuario.is_active and usuario.rol in roles


def rol_requerido(*roles):
    """Decorador para vistas de función: sin sesión → login; con sesión y otro rol → 403."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not tiene_rol(request.user, *roles):
                raise PermissionDenied
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador


admin_requerido = rol_requerido(Rol.ADMIN)


class RolRequeridoMixin(UserPassesTestMixin):
    """Mixin para vistas de clase: sin sesión → login; con sesión y otro rol → 403."""

    roles_permitidos = ()

    def test_func(self):
        return tiene_rol(self.request.user, *self.roles_permitidos)


class AdminRequeridoMixin(RolRequeridoMixin):
    """Toda operación de escritura (crear, editar, desactivar) usa este mixin o
    `admin_requerido`."""

    roles_permitidos = (Rol.ADMIN,)
