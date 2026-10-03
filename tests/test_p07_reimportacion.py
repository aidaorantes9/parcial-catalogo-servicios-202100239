"""P07: repetir la importación → ningún duplicado y resultado trazable.

También: la reimportación respeta lo que no viene del Excel (S7, S8): responsables (incluidas las
asignaciones de `cargar_demo`), baja lógica y estado REVISADO puesto por un administrador.
"""

from io import StringIO

import pytest
from django.core.management import call_command
from django.db.models import Count

from catalogo.models import ServicioNivel1, ServicioNivel2, TipoServicio
from importacion.models import Ejecucion, Observacion

pytestmark = [pytest.mark.django_db]


def _duplicados(modelo, campo):
    return modelo.objects.values(campo).annotate(n=Count("pk")).filter(n__gt=1).count()


@pytest.mark.p07
def test_p07_segunda_importacion_sin_duplicados(importar):
    """P07: la segunda importación da 0 creados y 0 actualizados, los mismos totales, ningún
    servicio ni observación duplicados y una nueva ejecución que vuelve a emitir las mismas
    observaciones."""
    importar()
    primera = Ejecucion.objects.get()
    observaciones = Observacion.objects.count()

    salida = importar()

    assert Ejecucion.objects.count() == 2
    segunda = Ejecucion.objects.exclude(pk=primera.pk).get()
    assert segunda.estado == "EXITOSA"
    assert (segunda.creados, segunda.actualizados) == (0, 0)
    assert segunda.sin_cambios == primera.creados == 76
    assert (segunda.omitidos, segunda.observados) == (primera.omitidos, primera.observados)
    assert (segunda.total_n1, segunda.total_n2) == (12, 46)
    assert "Creados: 0 · Actualizados: 0 · Sin cambios: 76" in salida
    assert "(0 nuevas)" in salida

    assert ServicioNivel1.objects.filter(origen__isnull=False).count() == 12
    assert ServicioNivel2.objects.count() == 46
    assert TipoServicio.objects.count() == 11
    assert _duplicados(ServicioNivel2, "codigo") == 0
    assert _duplicados(ServicioNivel2, "codigo_original") == 0
    assert Observacion.objects.count() == observaciones
    assert _duplicados(Observacion, "huella") == 0
    assert segunda.observaciones.count() == 0, "ninguna observación nueva"
    assert segunda.observaciones_emitidas.count() == observaciones

    origen = ServicioNivel2.objects.get(codigo="SE.12.3").origen
    assert origen.primera_ejecucion == primera and origen.ultima_ejecucion == segunda
    assert origen.ultima_accion == "SIN_CAMBIOS"


@pytest.mark.p07
def test_p07_la_ficha_sigue_mostrando_las_observaciones(importar, cliente_consulta):
    """Tras reimportar, la ficha muestra las observaciones vigentes (re-emitidas, no duplicadas)."""
    importar()
    importar()
    servicio = ServicioNivel2.objects.get(codigo="SE.12.3")
    contenido = cliente_consulta.get(servicio.get_absolute_url()).content.decode()
    assert contenido.count("Nivel 1 asignado por prefijo") == 1
    assert "Atributos ausentes" in contenido


@pytest.mark.p07
def test_p07_reimportacion_respeta_ediciones_manuales(importar):
    """S7/S8: se restauran los campos del Excel (cuenta como actualizado), pero no se tocan la
    baja lógica, el estado REVISADO ni el código funcional editado por un administrador."""
    importar()
    ServicioNivel2.objects.filter(codigo="SE.12.1").update(estado_revision="REVISADO")
    ServicioNivel2.objects.filter(codigo="SE.05.01").update(activo=False)
    ServicioNivel2.objects.filter(codigo="SE.03.01").update(nombre="Nombre editado")
    ServicioNivel2.objects.filter(codigo="SE.04.01").update(codigo="SE.04.01-EDITADO")

    importar()

    segunda = Ejecucion.objects.order_by("pk").last()
    assert (segunda.creados, segunda.actualizados) == (0, 1)
    assert ServicioNivel2.objects.get(codigo="SE.12.1").estado_revision == "REVISADO"
    assert ServicioNivel2.objects.get(codigo="SE.05.01").activo is False
    assert ServicioNivel2.objects.get(codigo="SE.03.01").nombre == (
        "Atender Soporte Usuario 1 Línea (HelpDesk)"
    )
    editado = ServicioNivel2.objects.get(codigo_original="SE.04.01")
    assert editado.codigo == "SE.04.01-EDITADO"
    assert ServicioNivel2.objects.count() == 46


@pytest.mark.p07
@pytest.mark.demo
def test_p07_reimportacion_no_borra_asignaciones_de_cargar_demo(importar, monkeypatch):
    """La reimportación no toca sección ni usuario responsables asignados por `cargar_demo`."""
    monkeypatch.delenv("DEMO_RESPONSABLE_PASSWORD", raising=False)
    importar()
    call_command("cargar_demo", stdout=StringIO())
    antes = dict(
        ServicioNivel2.objects.filter(seccion_responsable__isnull=False).values_list(
            "codigo", "usuario_responsable"
        )
    )
    assert len(antes) >= 3

    importar()

    despues = dict(
        ServicioNivel2.objects.filter(seccion_responsable__isnull=False).values_list(
            "codigo", "usuario_responsable"
        )
    )
    assert despues == antes
    assert Ejecucion.objects.order_by("pk").last().actualizados == 0
