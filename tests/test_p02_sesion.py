"""P02: acceso sin sesión, cierre de sesión y usuario inactivo."""

import pytest
from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.test import Client
from django.urls import reverse

from cuentas.forms import MENSAJE_LOGIN_INVALIDO
from cuentas.models import Usuario
from tests.conftest import PASSWORD

pytestmark = [pytest.mark.p02, pytest.mark.django_db]

URL_LOGIN = reverse("cuentas:entrar")


def _redirige_a_login(respuesta):
    return respuesta.status_code == 302 and respuesta.url.startswith(URL_LOGIN)


def _paginas_protegidas(usuario):
    return [
        reverse("inicio"),
        reverse("cuentas:perfil"),
        reverse("cuentas:usuario_lista"),
        reverse("cuentas:usuario_detalle", args=[usuario.pk]),
        reverse("cuentas:usuario_crear"),
    ]


def test_sin_sesion_se_rechazan_paginas_y_operaciones(client, consulta):
    """P02: sin sesión, toda página y operación protegida redirige al login y no modifica datos."""
    for url in _paginas_protegidas(consulta):
        assert _redirige_a_login(client.get(url)), url

    operaciones = {
        reverse("cuentas:usuario_crear"): {"username": "intruso", "email": "i@example.com"},
        reverse("cuentas:usuario_editar", args=[consulta.pk]): {"nombre": "Cambiado"},
        reverse("cuentas:usuario_desactivar", args=[consulta.pk]): {},
        reverse("cuentas:usuario_password", args=[consulta.pk]): {"new_password1": "x"},
    }
    for url, datos in operaciones.items():
        assert _redirige_a_login(client.post(url, datos)), url

    consulta.refresh_from_db()
    assert consulta.is_active and consulta.nombre == "Consulta"
    assert not Usuario.objects.filter(username="intruso").exists()


def test_login_y_salud_no_requieren_sesion(client):
    """P02: las únicas excepciones son el login y el healthcheck."""
    assert client.get(URL_LOGIN).status_code == 200
    assert client.get(reverse("salud")).status_code == 200


def test_logout_invalida_la_sesion_en_el_servidor(client, consulta):
    """P02: tras el logout, la cookie de sesión anterior ya no da acceso."""
    assert client.post(URL_LOGIN, {"username": "consulta", "password": PASSWORD}).status_code == 302
    cookie = client.cookies[settings.SESSION_COOKIE_NAME].value
    assert Session.objects.filter(session_key=cookie).exists()

    respuesta = client.post(reverse("cuentas:salir"))
    assert respuesta.status_code == 302
    assert not Session.objects.filter(session_key=cookie).exists()

    # Un cliente nuevo que reutiliza la cookie capturada antes del logout.
    reutiliza = Client()
    reutiliza.cookies[settings.SESSION_COOKIE_NAME] = cookie
    assert _redirige_a_login(reutiliza.get(reverse("inicio")))


def test_logout_solo_por_post(cliente_consulta):
    """P02: GET a /salir/ no cierra la sesión (405); evita cierres por enlaces de terceros."""
    assert cliente_consulta.get(reverse("cuentas:salir")).status_code == 405
    assert cliente_consulta.get(reverse("inicio")).status_code == 200


def test_logout_exige_token_csrf(consulta):
    """P02: un POST de logout sin token CSRF se rechaza con 403."""
    cliente = Client(enforce_csrf_checks=True)
    cliente.force_login(consulta)
    assert cliente.post(reverse("cuentas:salir")).status_code == 403


def test_usuario_inactivo_no_puede_iniciar_sesion(client, consulta):
    """P02: un usuario desactivado no inicia sesión y recibe el mensaje genérico."""
    consulta.is_active = False
    consulta.save()
    respuesta = client.post(URL_LOGIN, {"username": "consulta", "password": PASSWORD})
    assert respuesta.status_code == 200
    assert MENSAJE_LOGIN_INVALIDO in respuesta.content.decode()
    assert SESSION_KEY not in client.session


def test_sesion_abierta_de_usuario_desactivado_se_invalida(client, consulta, cliente_admin):
    """P02: si se desactiva con la sesión abierta, su siguiente petición se rechaza y la sesión se
    borra del servidor (no vuelve a servir aunque se reactive)."""
    sesion_consulta = Client()
    sesion_consulta.post(URL_LOGIN, {"username": "consulta", "password": PASSWORD})
    cookie = sesion_consulta.cookies[settings.SESSION_COOKIE_NAME].value
    assert sesion_consulta.get(reverse("inicio")).status_code == 200

    # El administrador lo desactiva por la interfaz.
    cliente_admin.post(reverse("cuentas:usuario_desactivar", args=[consulta.pk]))
    consulta.refresh_from_db()
    assert not consulta.is_active

    assert _redirige_a_login(sesion_consulta.get(reverse("inicio")))
    assert not Session.objects.filter(session_key=cookie).exists()

    consulta.is_active = True
    consulta.save()
    reutiliza = Client()
    reutiliza.cookies[settings.SESSION_COOKIE_NAME] = cookie
    assert _redirige_a_login(reutiliza.get(reverse("inicio")))


def test_cambio_de_password_invalida_sesiones_del_usuario(consulta, cliente_admin):
    """P02: al cambiar la contraseña de un usuario, sus sesiones abiertas dejan de servir."""
    sesion_consulta = Client()
    sesion_consulta.post(URL_LOGIN, {"username": "consulta", "password": PASSWORD})
    nueva = "Otra-Clave-Segura-2026?"
    respuesta = cliente_admin.post(
        reverse("cuentas:usuario_password", args=[consulta.pk]),
        {"new_password1": nueva, "new_password2": nueva},
    )
    assert respuesta.status_code == 302
    assert _redirige_a_login(sesion_consulta.get(reverse("inicio")))
