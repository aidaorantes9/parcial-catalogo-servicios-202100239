"""Mantenimiento de usuarios por ADMIN.

Complementa P03: la escritura sí funciona con el rol correcto.
"""

import pytest
from django.urls import reverse

from cuentas.models import Rol, Usuario

pytestmark = [pytest.mark.p03, pytest.mark.django_db]

CLAVE = "Clave-Nueva-Segura-2026!"


def _datos_alta(puesto, **cambios):
    datos = {
        "username": "nuevo",
        "email": "nuevo@example.com",
        "nombre": "Usuario Nuevo",
        "rol": Rol.CONSULTA,
        "puesto": puesto.pk,
        "password1": CLAVE,
        "password2": CLAVE,
    }
    datos.update(cambios)
    return datos


def test_admin_crea_usuario_con_hash(cliente_admin, puesto):
    """P03: ADMIN crea un usuario; la contraseña queda con hash Argon2."""
    respuesta = cliente_admin.post(reverse("cuentas:usuario_crear"), _datos_alta(puesto))
    assert respuesta.status_code == 302
    usuario = Usuario.objects.get(username="nuevo")
    assert usuario.password.startswith("argon2$") and usuario.check_password(CLAVE)
    assert usuario.empresa == puesto.seccion.departamento.area.empresa


def test_alta_rechaza_password_debil_y_duplicados(cliente_admin, puesto, admin):
    """P03: validadores de contraseña de Django y unicidad sin distinguir mayúsculas."""
    url = reverse("cuentas:usuario_crear")
    assert (
        cliente_admin.post(url, _datos_alta(puesto, password1="123", password2="123")).status_code
        == 200
    )
    assert cliente_admin.post(url, _datos_alta(puesto, username="ADMIN")).status_code == 200
    assert (
        cliente_admin.post(url, _datos_alta(puesto, email="ADMIN@example.com")).status_code == 200
    )
    assert not Usuario.objects.filter(username__in=["nuevo", "ADMIN"]).exists()


def test_alta_rechaza_puesto_inactivo(cliente_admin, puesto):
    """P03: no se asigna un usuario a un puesto inactivo."""
    puesto.activo = False
    puesto.save()
    respuesta = cliente_admin.post(reverse("cuentas:usuario_crear"), _datos_alta(puesto))
    assert respuesta.status_code == 200
    assert not Usuario.objects.filter(username="nuevo").exists()


def test_admin_edita_desactiva_y_reactiva(cliente_admin, consulta, puesto):
    """P03: ADMIN edita nombre, correo y rol; desactiva y reactiva (baja lógica, sin borrar)."""
    url = reverse("cuentas:usuario_editar", args=[consulta.pk])
    datos = {
        "nombre": "Nombre Nuevo",
        "email": "otro@example.com",
        "rol": Rol.ADMIN,
        "puesto": puesto.pk,
    }
    assert cliente_admin.post(url, datos).status_code == 302
    consulta.refresh_from_db()
    assert (consulta.nombre, consulta.email, consulta.rol) == (
        "Nombre Nuevo",
        "otro@example.com",
        Rol.ADMIN,
    )

    cliente_admin.post(reverse("cuentas:usuario_desactivar", args=[consulta.pk]))
    consulta.refresh_from_db()
    assert not consulta.is_active
    cliente_admin.post(reverse("cuentas:usuario_reactivar", args=[consulta.pk]))
    consulta.refresh_from_db()
    assert consulta.is_active


def test_admin_no_puede_desactivarse_ni_quitarse_el_rol(cliente_admin, admin, puesto):
    """P03: un administrador no puede desactivarse a sí mismo ni quitarse el rol ADMIN."""
    cliente_admin.post(reverse("cuentas:usuario_desactivar", args=[admin.pk]))
    admin.refresh_from_db()
    assert admin.is_active

    url = reverse("cuentas:usuario_editar", args=[admin.pk])
    datos = {"nombre": "A", "email": admin.email, "rol": Rol.CONSULTA, "puesto": puesto.pk}
    assert cliente_admin.post(url, datos).status_code == 200
    admin.refresh_from_db()
    assert admin.rol == Rol.ADMIN


def test_desactivar_y_reactivar_solo_por_post(cliente_admin, consulta):
    """P03: GET a desactivar no cambia el estado (405)."""
    assert (
        cliente_admin.get(reverse("cuentas:usuario_desactivar", args=[consulta.pk])).status_code
        == 405
    )
    consulta.refresh_from_db()
    assert consulta.is_active


def test_listado_paginado_con_busqueda(cliente_admin, crear_usuario):
    """P03: listado con búsqueda por usuario, nombre o correo y paginación de 20."""
    for i in range(25):
        crear_usuario(f"persona{i:02d}")
    respuesta = cliente_admin.get(reverse("cuentas:usuario_lista"))
    assert respuesta.context["is_paginated"] and len(respuesta.context["usuarios"]) == 20
    respuesta = cliente_admin.get(reverse("cuentas:usuario_lista"), {"q": "persona07"})
    assert [u.username for u in respuesta.context["usuarios"]] == ["persona07"]
