"""Comando `cargar_demo`: al menos tres asignaciones válidas (enunciado §3.3) e idempotencia."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from catalogo.models import ServicioNivel2
from cuentas.models import Rol, Usuario
from organizacion.models import Puesto, Seccion

pytestmark = [pytest.mark.demo, pytest.mark.django_db]

PASSWORD_DEMO = "Responsable-Demo-2026!"


def cargar():
    salida = StringIO()
    call_command("cargar_demo", stdout=salida)
    return salida.getvalue()


def asignaciones():
    return list(
        ServicioNivel2.objects.filter(seccion_responsable__isnull=False)
        .select_related("seccion_responsable", "usuario_responsable__puesto")
        .order_by("codigo")
    )


@pytest.fixture(autouse=True)
def sin_password_demo(monkeypatch):
    monkeypatch.delenv("DEMO_RESPONSABLE_PASSWORD", raising=False)


def test_cargar_demo_requiere_catalogo_importado(db):
    """Sin catálogo importado falla con un mensaje claro y no crea nada."""
    with pytest.raises(CommandError, match="no está importado"):
        cargar()
    assert not Seccion.objects.exists() and not Usuario.objects.exists()


def test_cargar_demo_crea_tres_asignaciones_validas_e_idempotente(importar):
    """Al menos 3 asignaciones sobre servicios importados, en 2 secciones DEMO distintas, con un
    usuario responsable CONSULTA de la misma sección. Repetirlo no duplica ni cambia nada."""
    importar()
    salida = cargar()
    lista = asignaciones()

    assert len(lista) >= 3
    assert len({s.seccion_responsable_id for s in lista}) >= 2
    assert all(s.origen for s in lista), "solo servicios importados"
    assert all(s.seccion_responsable.es_demo for s in lista), "marcadas como demostración"
    con_usuario = [s for s in lista if s.usuario_responsable]
    assert con_usuario
    for s in con_usuario:
        assert s.usuario_responsable.puesto.seccion_id == s.seccion_responsable_id
        assert s.usuario_responsable.rol == Rol.CONSULTA
        assert s.usuario_responsable.puesto.es_demo
        assert not s.usuario_responsable.has_usable_password()
    for s in lista:
        s.full_clean()  # D9: la asignación es válida con las reglas del modelo
    assert "Total: 4 asignaciones, 2 secciones, 2 con usuario responsable." in salida

    conteos = (Seccion.objects.count(), Puesto.objects.count(), Usuario.objects.count())
    estado = [(s.codigo, s.seccion_responsable_id, s.usuario_responsable_id) for s in lista]
    segunda = cargar()
    assert (Seccion.objects.count(), Puesto.objects.count(), Usuario.objects.count()) == conteos
    assert [
        (s.codigo, s.seccion_responsable_id, s.usuario_responsable_id) for s in asignaciones()
    ] == estado
    assert "sin cambios" in segunda


def test_cargar_demo_usa_la_password_del_entorno(importar, monkeypatch):
    """Con DEMO_RESPONSABLE_PASSWORD definida, los usuarios demo pueden iniciar sesión con ella."""
    monkeypatch.setenv("DEMO_RESPONSABLE_PASSWORD", PASSWORD_DEMO)
    importar()
    cargar()
    usuario = Usuario.objects.get(username="demo.infraestructura")
    assert usuario.check_password(PASSWORD_DEMO)
    assert usuario.password.startswith("argon2")


def test_cargar_demo_no_sobrescribe_una_asignacion_existente(importar, puesto):
    """Una asignación hecha por un administrador se conserva; el mínimo se cumple igual."""
    importar()
    servicio = ServicioNivel2.objects.get(codigo="SE.01.01")
    servicio.seccion_responsable = puesto.seccion
    servicio.save()

    salida = cargar()

    servicio.refresh_from_db()
    assert servicio.seccion_responsable == puesto.seccion
    assert servicio.usuario_responsable is None
    assert "SE.01.01: ya tiene otra asignación" in salida
    assert "Total: 3 asignaciones, 2 secciones, 1 con usuario responsable." in salida
