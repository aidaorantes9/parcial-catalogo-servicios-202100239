"""Comando crear_cuentas_demo: idempotencia y error si falta una variable."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from cuentas.models import Rol, Usuario
from organizacion.models import Empresa, Puesto

pytestmark = [pytest.mark.django_db]

ENTORNO = {
    "DEMO_ADMIN_USUARIO": "admin.prueba",
    "DEMO_ADMIN_CORREO": "admin.prueba@example.com",
    "DEMO_ADMIN_PASSWORD": "Prueba-Admin-Demo-2026",
    "DEMO_CONSULTA_USUARIO": "consulta.prueba",
    "DEMO_CONSULTA_CORREO": "consulta.prueba@example.com",
    "DEMO_CONSULTA_PASSWORD": "Clave-Lectura-Xq7-2026",
}


@pytest.fixture
def entorno(monkeypatch):
    for nombre, valor in ENTORNO.items():
        monkeypatch.setenv(nombre, valor)
    return monkeypatch


def test_crea_jerarquia_demo_y_cuentas(entorno):
    call_command("crear_cuentas_demo")
    admin = Usuario.objects.get(username="admin.prueba")
    consulta = Usuario.objects.get(username="consulta.prueba")
    assert admin.rol == Rol.ADMIN and consulta.rol == Rol.CONSULTA
    assert admin.check_password(ENTORNO["DEMO_ADMIN_PASSWORD"])
    assert admin.password.startswith("argon2$")
    assert admin.puesto == consulta.puesto and admin.puesto.es_demo
    assert admin.empresa.codigo == "DEMO" and admin.empresa.es_demo


def test_idempotente_no_duplica_ni_cambia_password(entorno):
    call_command("crear_cuentas_demo")
    entorno.setenv("DEMO_ADMIN_PASSWORD", "Otra-Clave-Distinta-2026")
    call_command("crear_cuentas_demo")
    assert Usuario.objects.count() == 2
    assert Empresa.objects.count() == 1 and Puesto.objects.count() == 1
    admin = Usuario.objects.get(username="admin.prueba")
    assert admin.check_password(ENTORNO["DEMO_ADMIN_PASSWORD"])


def test_restablecer_cambia_password(entorno):
    call_command("crear_cuentas_demo")
    entorno.setenv("DEMO_ADMIN_PASSWORD", "Otra-Clave-Distinta-2026")
    call_command("crear_cuentas_demo", "--restablecer")
    assert Usuario.objects.count() == 2
    assert Usuario.objects.get(username="admin.prueba").check_password("Otra-Clave-Distinta-2026")


@pytest.mark.parametrize("faltante", sorted(ENTORNO))
def test_falla_si_falta_una_variable(entorno, faltante):
    entorno.delenv(faltante)
    with pytest.raises(CommandError, match=faltante):
        call_command("crear_cuentas_demo")
    assert Usuario.objects.count() == 0 and Empresa.objects.count() == 0


def test_falla_con_variable_vacia(entorno):
    entorno.setenv("DEMO_CONSULTA_CORREO", "   ")
    with pytest.raises(CommandError, match="DEMO_CONSULTA_CORREO"):
        call_command("crear_cuentas_demo")
