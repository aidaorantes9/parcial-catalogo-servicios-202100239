"""P03: el usuario de consulta intenta modificar datos.

Rechazo en el servidor; lectura permitida.
"""

import pytest
from django.urls import reverse

from cuentas.models import Rol, Usuario
from tests.conftest import PASSWORD

pytestmark = [pytest.mark.p03, pytest.mark.django_db]


@pytest.fixture
def victima(crear_usuario):
    return crear_usuario("victima")


def test_consulta_recibe_403_en_operaciones_de_escritura(cliente_consulta, victima, puesto):
    """P03: POST directo (sin botón) de crear, editar, desactivar, reactivar y cambiar
    contraseña → 403 y los datos no cambian."""
    nueva = "Clave-Nueva-Segura-2026!"
    operaciones = {
        reverse("cuentas:usuario_crear"): {
            "username": "nuevo",
            "email": "nuevo@example.com",
            "nombre": "Nuevo",
            "rol": Rol.ADMIN,
            "puesto": puesto.pk,
            "password1": nueva,
            "password2": nueva,
        },
        reverse("cuentas:usuario_editar", args=[victima.pk]): {
            "nombre": "Cambiado",
            "email": "cambiado@example.com",
            "rol": Rol.ADMIN,
            "puesto": puesto.pk,
        },
        reverse("cuentas:usuario_desactivar", args=[victima.pk]): {},
        reverse("cuentas:usuario_reactivar", args=[victima.pk]): {},
        reverse("cuentas:usuario_password", args=[victima.pk]): {
            "new_password1": nueva,
            "new_password2": nueva,
        },
    }
    for url, datos in operaciones.items():
        assert cliente_consulta.post(url, datos).status_code == 403, url

    victima.refresh_from_db()
    assert victima.nombre == "Victima" and victima.rol == Rol.CONSULTA and victima.is_active
    assert victima.check_password(PASSWORD)
    assert not Usuario.objects.filter(username="nuevo").exists()


def test_consulta_no_puede_escalar_su_propio_rol(cliente_consulta, consulta, puesto):
    """P03: tampoco puede editarse a sí mismo para volverse administrador."""
    url = reverse("cuentas:usuario_editar", args=[consulta.pk])
    datos = {"nombre": "X", "email": consulta.email, "rol": Rol.ADMIN, "puesto": puesto.pk}
    assert cliente_consulta.post(url, datos).status_code == 403
    consulta.refresh_from_db()
    assert consulta.rol == Rol.CONSULTA


def test_consulta_puede_leer_paginas_de_lectura(cliente_consulta):
    """P03: GET de las páginas de lectura de su rol permitido (200)."""
    for url in [reverse("inicio"), reverse("cuentas:perfil")]:
        assert cliente_consulta.get(url).status_code == 200, url


def test_consulta_no_accede_al_mantenimiento_de_usuarios(cliente_consulta, victima):
    """P03: las pantallas de mantenimiento de usuarios son solo de ADMIN (403 también en GET)."""
    for url in [
        reverse("cuentas:usuario_lista"),
        reverse("cuentas:usuario_detalle", args=[victima.pk]),
        reverse("cuentas:usuario_crear"),
        reverse("cuentas:usuario_editar", args=[victima.pk]),
        reverse("cuentas:usuario_password", args=[victima.pk]),
    ]:
        assert cliente_consulta.get(url).status_code == 403, url


def test_consulta_no_ve_hashes_de_ningun_usuario(cliente_consulta, consulta, admin, victima):
    """P03: ninguna respuesta que recibe CONSULTA contiene un hash de contraseña."""
    hashes = list(Usuario.objects.values_list("password", flat=True))
    urls = [
        reverse("inicio"),
        reverse("cuentas:perfil"),
        reverse("cuentas:usuario_lista"),
        *[reverse("cuentas:usuario_detalle", args=[u.pk]) for u in (consulta, admin, victima)],
    ]
    for url in urls:
        contenido = cliente_consulta.get(url).content.decode()
        assert "argon2" not in contenido, url
        assert all(h not in contenido for h in hashes), url


def test_admin_tampoco_ve_hashes(cliente_admin, consulta):
    """P03: las pantallas de administración tampoco muestran hashes."""
    for url in [
        reverse("cuentas:usuario_lista"),
        reverse("cuentas:usuario_detalle", args=[consulta.pk]),
        reverse("cuentas:usuario_editar", args=[consulta.pk]),
        reverse("cuentas:usuario_password", args=[consulta.pk]),
    ]:
        respuesta = cliente_admin.get(url)
        assert respuesta.status_code == 200, url
        assert "argon2" not in respuesta.content.decode(), url
