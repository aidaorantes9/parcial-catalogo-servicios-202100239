from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsuarioOCorreoBackend(ModelBackend):
    """Autentica con usuario **o** correo (sin distinguir mayúsculas) contra la base propia.

    Rechaza usuarios inactivos (`user_can_authenticate`) y, al restaurar la sesión en cada petición,
    `get_user` de ModelBackend también devuelve None si el usuario fue desactivado.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or password is None:
            return None
        identificador = username.strip()
        Usuario = get_user_model()
        candidatos = list(
            Usuario._default_manager.filter(
                Q(username__iexact=identificador) | Q(email__iexact=identificador)
            )[:2]
        )
        if len(candidatos) != 1:
            # Inexistente (o ambiguo): se calcula un hash igualmente para que el tiempo de respuesta
            # no revele si el usuario existe.
            Usuario().set_password(password)
            return None
        usuario = candidatos[0]
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
