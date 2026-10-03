from django.contrib.auth import views as auth_views
from django.urls import path

from cuentas import views
from cuentas.forms import LoginForm

app_name = "cuentas"

urlpatterns = [
    path(
        "entrar/",
        auth_views.LoginView.as_view(
            template_name="cuentas/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name="entrar",
    ),
    # LogoutView solo acepta POST (GET → 405) y llama a logout(), que hace session.flush().
    path("salir/", auth_views.LogoutView.as_view(), name="salir"),
    path("perfil/", views.perfil, name="perfil"),
    path("usuarios/", views.UsuarioListaView.as_view(), name="usuario_lista"),
    path("usuarios/nuevo/", views.UsuarioCrearView.as_view(), name="usuario_crear"),
    path("usuarios/<int:pk>/", views.UsuarioDetalleView.as_view(), name="usuario_detalle"),
    path("usuarios/<int:pk>/editar/", views.UsuarioEditarView.as_view(), name="usuario_editar"),
    path(
        "usuarios/<int:pk>/desactivar/",
        views.UsuarioCambiarEstadoView.as_view(activar=False),
        name="usuario_desactivar",
    ),
    path(
        "usuarios/<int:pk>/reactivar/",
        views.UsuarioCambiarEstadoView.as_view(activar=True),
        name="usuario_reactivar",
    ),
    path(
        "usuarios/<int:pk>/contrasena/",
        views.UsuarioCambiarPasswordView.as_view(),
        name="usuario_password",
    ),
]
