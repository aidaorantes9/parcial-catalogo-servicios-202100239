"""Migración cuentas 0002/0003 (Usuario.puesto) sobre una base que ya tiene usuarios."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

ANTES = [("cuentas", "0001_initial"), ("organizacion", "0001_initial")]
DESPUES = [("cuentas", "0003_usuario_puesto_obligatorio"), ("organizacion", "0001_initial")]


def _migrar(destino):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(destino)
    return executor.loader.project_state(destino).apps


@pytest.mark.django_db(transaction=True)
def test_usuarios_previos_quedan_en_puesto_transitorio_inactivo():
    apps = _migrar(ANTES)
    Usuario = apps.get_model("cuentas", "Usuario")
    Usuario.objects.create(username="previo", email="previo@example.com", nombre="Previo")
    try:
        apps = _migrar(DESPUES)
        usuario = apps.get_model("cuentas", "Usuario").objects.get(username="previo")
        puesto = usuario.puesto
        assert puesto.codigo == "MIGRACION" and not puesto.activo
        assert usuario.is_active  # no se desactiva ni se borra a nadie
    finally:
        _migrar(DESPUES)
        apps.get_model("cuentas", "Usuario").objects.all().delete()


@pytest.mark.django_db(transaction=True)
def test_base_vacia_no_crea_jerarquia_transitoria():
    _migrar(ANTES)
    apps = _migrar(DESPUES)
    assert not apps.get_model("organizacion", "Empresa").objects.filter(codigo="MIGRACION").exists()
