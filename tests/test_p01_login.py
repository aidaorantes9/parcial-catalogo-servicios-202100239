"""P01: inicio de sesión válido e inválido."""

import pytest
from django.contrib.auth import SESSION_KEY
from django.urls import reverse

from cuentas.forms import MENSAJE_LOGIN_INVALIDO
from tests.conftest import PASSWORD

pytestmark = [pytest.mark.p01, pytest.mark.django_db]

URL_LOGIN = reverse("cuentas:entrar")


def _entrar(client, identificador, password):
    return client.post(URL_LOGIN, {"username": identificador, "password": password})


@pytest.mark.parametrize(
    "identificador", ["admin", "ADMIN", "admin@example.com", "ADMIN@EXAMPLE.COM"]
)
def test_login_valido_con_usuario_o_correo(client, admin, identificador):
    """P01: login correcto con nombre de usuario o correo, sin distinguir mayúsculas."""
    respuesta = _entrar(client, identificador, PASSWORD)
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("inicio")
    assert client.session[SESSION_KEY] == str(admin.pk)
    assert client.get(reverse("inicio")).status_code == 200


@pytest.mark.parametrize(
    ("identificador", "password"),
    [("admin", "contraseña-incorrecta"), ("admin@example.com", "otra"), ("no-existe", PASSWORD)],
)
def test_login_invalido_rechazado_con_mensaje_generico(client, admin, identificador, password):
    """P01: contraseña incorrecta o usuario inexistente → sin sesión y el mismo mensaje genérico."""
    respuesta = _entrar(client, identificador, password)
    assert respuesta.status_code == 200
    assert SESSION_KEY not in client.session
    assert MENSAJE_LOGIN_INVALIDO in respuesta.content.decode()
    assert client.get(reverse("inicio")).status_code == 302


def test_password_guardada_con_argon2(admin):
    """P01: la contraseña se guarda con hash Argon2 con sal, nunca en texto plano."""
    assert admin.password.startswith("argon2$argon2id$")
    assert PASSWORD not in admin.password
    assert admin.check_password(PASSWORD)
