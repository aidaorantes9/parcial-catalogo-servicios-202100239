"""Referencias inactivas: dar de baja un nivel 1 o un valor de catálogo usado por el Excel no debe
dejar inutilizable la reimportación (P07: la importación se puede repetir).

Las bajas se hacen por la vía normal de administración (D1: primero los servicios dependientes,
luego el nivel 1 o el valor de catálogo), con `full_clean()`.
"""

import pytest
from django.core.management.base import CommandError
from django.db.models import Count

from catalogo.models import ServicioNivel1, ServicioNivel2, TipoServicio
from catalogo.servicios import guardar_servicio_nivel2
from importacion.models import Ejecucion, Observacion

pytestmark = [pytest.mark.importacion, pytest.mark.p07, pytest.mark.django_db]


def _dar_de_baja(registro):
    registro.activo = False
    if isinstance(registro, ServicioNivel2):
        guardar_servicio_nivel2(registro)
    else:
        registro.full_clean()
        registro.save()


def test_reimportar_con_nivel1_y_tipo_dados_de_baja(importar):
    """Con SE.11 y el tipo «IT Management» dados de baja, la reimportación termina bien: los
    servicios afectados conservan sus valores actuales (se cuentan como observados, no como
    actualizados), aparece REFERENCIA_INACTIVA con código, columna, fila y valor, y no se pierde
    ni duplica nada."""
    importar()
    se11 = ServicioNivel1.objects.get(codigo="SE.11")
    tipo = TipoServicio.objects.get(etiqueta_original="IT Management")
    por_n1 = list(se11.servicios_nivel2.order_by("codigo"))
    por_tipo = list(tipo.servicios.order_by("codigo"))
    assert por_n1 and por_tipo
    for servicio in {s.pk: s for s in por_n1 + por_tipo}.values():
        _dar_de_baja(servicio)
    _dar_de_baja(se11)
    _dar_de_baja(tipo)
    # Edición manual que la reimportación no debe pisar en un servicio observado.
    editado = ServicioNivel2.objects.get(codigo="SE.11.01")
    editado.nombre = "Nombre editado"
    editado.save()

    salida = importar()

    ejecucion = Ejecucion.objects.order_by("pk").last()
    assert ejecucion.estado == "EXITOSA"
    assert (ejecucion.total_n1, ejecucion.total_n2) == (12, 46)
    afectados = {s.codigo for s in por_n1} | {s.codigo for s in por_tipo}
    conteo = ejecucion.detalle_conteos["nivel2"]
    assert conteo["observados"] == len(afectados)
    assert (conteo["creados"], conteo["actualizados"]) == (0, 0)
    assert "Registros observados (referencia inactiva, sin cambios aplicados): " in salida
    assert "→ PASA" in salida and "FALLA" not in salida

    for servicio in por_n1:
        obs = Observacion.objects.get(
            tipo="REFERENCIA_INACTIVA",
            codigo_afectado=servicio.codigo,
            valores_conflicto__campo="nivel1",
        )
        fila = servicio.origen.filas[0]
        assert obs.valores_conflicto == {
            "columna": "A",
            "fila": fila,
            "valor": "SE.11",
            "campo": "nivel1",
        }
        assert obs.servicio_nivel2_id == servicio.pk
    for servicio in por_tipo:
        obs = Observacion.objects.get(
            tipo="REFERENCIA_INACTIVA",
            codigo_afectado=servicio.codigo,
            valores_conflicto__campo="tipo",
        )
        assert obs.valores_conflicto["columna"] == "H"
        assert obs.valores_conflicto["valor"] == "IT Management"
        assert obs.celdas == [f"H{servicio.origen.filas[0]}"]

    for codigo in afectados:
        servicio = ServicioNivel2.objects.get(codigo_original=codigo)
        assert servicio.activo is False, "S8: la baja lógica no se revierte"
        assert servicio.origen.ultima_accion == "OBSERVADO"
        assert servicio.origen.ultima_ejecucion == ejecucion
    assert ServicioNivel2.objects.get(codigo="SE.11.01").nombre == "Nombre editado"
    assert {
        s.tipo_id for s in ServicioNivel2.objects.filter(codigo__in=[s.codigo for s in por_tipo])
    } == {tipo.pk}

    assert ServicioNivel2.objects.count() == 46
    assert ServicioNivel1.objects.count() == 12
    assert TipoServicio.objects.count() == 11
    duplicados = ServicioNivel2.objects.values("codigo_original").annotate(n=Count("pk"))
    assert not duplicados.filter(n__gt=1).exists()

    # Repetirla otra vez no duplica observaciones.
    total_obs = Observacion.objects.count()
    importar()
    assert Observacion.objects.count() == total_obs
    assert Ejecucion.objects.order_by("pk").last().detalle_conteos["nivel2"]["observados"] == len(
        afectados
    )


def test_servicio_nuevo_con_nivel1_inactivo_no_se_crea(importar, excel_modificado):
    """Un servicio nuevo cuyo nivel 1 está inactivo no se crea: se cuenta como omitido y se registra
    REFERENCIA_INACTIVA. Los controles cuentan registros existentes, así que con el archivo
    original (controles exigidos) la importación falla 12/43; con otro archivo solo se informa."""
    ServicioNivel1.objects.create(codigo="SE.12", nombre="Creado antes", activo=False)

    with pytest.raises(CommandError, match="Controles no superados"):
        importar()
    fallida = Ejecucion.objects.get()
    assert (fallida.estado, fallida.total_n2) == ("FALLIDA", 43)

    salida = importar("--archivo", excel_modificado({}))

    assert not ServicioNivel2.objects.filter(codigo__startswith="SE.12.").exists()
    assert ServicioNivel2.objects.count() == 43
    ejecucion = Ejecucion.objects.exclude(pk=fallida.pk).get()
    assert ejecucion.estado == "EXITOSA"
    assert ejecucion.detalle_conteos["filas"]["referencia_inactiva"] == 3
    assert ejecucion.omitidos == 51 + 3
    obs = Observacion.objects.filter(tipo="REFERENCIA_INACTIVA").order_by("codigo_afectado")
    assert [o.codigo_afectado for o in obs] == ["SE.12.1", "SE.12.2", "SE.12.3"]
    assert [o.valores_conflicto["fila"] for o in obs] == [99, 100, 101]
    assert all(o.servicio_nivel2 is None for o in obs)
    assert "servicios nuevos no creados: nivel 1 inactivo (omitidos) → [99, 100, 101]" in salida
    assert "FALLA (informativo" in salida
    assert ServicioNivel1.objects.get(codigo="SE.12").activo is False
