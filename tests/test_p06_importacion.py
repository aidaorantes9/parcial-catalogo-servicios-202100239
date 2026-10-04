"""P06: importar el archivo original → 12 códigos de nivel 1, 46 de nivel 2 e incidencias.

Se importa el Excel real (data/, montado en solo lectura). También: filas de continuación y filas
42 y 67 que no crean servicios, trazabilidad del origen, hash distinto, dry-run y controles.
"""

import hashlib
from pathlib import Path

import pytest
from django.core.management.base import CommandError

from catalogo.models import ClaseServicio, Criticidad, ServicioNivel1, ServicioNivel2, TipoServicio
from importacion.models import Ejecucion, Observacion, OrigenServicio

pytestmark = [pytest.mark.django_db]

SHA_ORIGINAL = "de3b478a5faeeeaebce1aa7726e0e3321188a68e41bbb656e1d17b0c5b74dcf0"

OBSERVACIONES_ESPERADAS = {
    "ATRIBUTOS_AUSENTES": 3,
    "AUSENCIA_EN_CONTINUACION": 1,
    "CODIGO_FORMATO_NO_ESTANDAR": 3,
    "CONFLICTO_NOMBRE_N1": 1,
    "CONTROL_CONTEO": 2,
    "CORRECCION_APLICADA": 1,
    "ESPACIOS_EN_TEXTO": 1,
    "FILA_SIN_CODIGO": 2,
    "PADRE_POR_PREFIJO": 1,
    "POSIBLE_ERROR_ESCRITURA": 1,
    "TEXTO_CON_FORMA_DE_INSTRUCCION": 1,
}
FILAS_SIN_CODIGO = {
    42: {"E": "S", "F": "RECURRENTE", "G": "Normal", "H": "Front End"},
    67: {"E": "S", "F": "A DEMANDA", "G": "Normal", "H": "Front End"},
}


def _por_tipo():
    conteo = {}
    for tipo in Observacion.objects.values_list("tipo", flat=True):
        conteo[tipo] = conteo.get(tipo, 0) + 1
    return conteo


@pytest.mark.p06
def test_p06_importar_original_produce_12_n1_y_46_n2(importar):
    """P06: 12 códigos de nivel 1 y 46 servicios de nivel 2, cada uno con su nivel 1; catálogos
    desde E112:H122; resumen con controles PASA y ejecución EXITOSA con sus conteos."""
    salida = importar()

    importados_n1 = ServicioNivel1.objects.filter(origen__isnull=False)
    importados_n2 = ServicioNivel2.objects.filter(origen__isnull=False)
    assert importados_n1.count() == 12
    assert importados_n2.count() == 46
    assert sorted(importados_n1.values_list("codigo", flat=True)) == [
        f"SE.{n:02d}" for n in range(1, 13)
    ]
    assert not importados_n2.filter(nivel1__isnull=True).exists()
    assert all(s.codigo == s.codigo_original and s.activo for s in importados_n2), (
        "codigo = codigo_original (D5) y todo importado entra activo (D8)"
    )
    assert (ClaseServicio.objects.count(), Criticidad.objects.count()) == (2, 5)
    assert TipoServicio.objects.count() == 11

    ejecucion = Ejecucion.objects.get()
    assert ejecucion.estado == "EXITOSA"
    assert (ejecucion.total_n1, ejecucion.total_n2) == (12, 46)
    assert ejecucion.creados == 2 + 5 + 11 + 12 + 46
    assert (ejecucion.actualizados, ejecucion.sin_cambios) == (0, 0)
    assert ejecucion.omitidos == 51  # 49 de continuación + filas 42 y 67
    assert ejecucion.observados == sum(OBSERVACIONES_ESPERADAS.values())
    assert ejecucion.archivo_sha256 == SHA_ORIGINAL
    assert ejecucion.detalle_conteos["archivo_original"] is True
    assert "Códigos de nivel 1: 12 / esperado 12 → PASA" in salida
    assert "Códigos de nivel 2: 46 / esperado 46 → PASA" in salida
    assert "FALLA" not in salida


@pytest.mark.p06
def test_p06_incidencias_registradas(importar):
    """P06: se registran las observaciones esperadas (SE.12, SE.12.3, filas 42 y 67, ausencias,
    errores de escritura, I5) enlazadas a su servicio."""
    importar()
    assert _por_tipo() == OBSERVACIONES_ESPERADAS

    conflicto = Observacion.objects.get(tipo="CONFLICTO_NOMBRE_N1")
    assert conflicto.servicio_nivel1.codigo == "SE.12"
    assert conflicto.celdas == ["B99", "B100"]

    prefijo = Observacion.objects.get(tipo="PADRE_POR_PREFIJO")
    assert prefijo.servicio_nivel2.codigo == "SE.12.3" and prefijo.filas == [101]

    ausentes = Observacion.objects.filter(tipo="ATRIBUTOS_AUSENTES")
    assert sorted(o.servicio_nivel2.codigo for o in ausentes) == ["SE.12.1", "SE.12.2", "SE.12.3"]
    formato = Observacion.objects.filter(tipo="CODIGO_FORMATO_NO_ESTANDAR")
    assert sorted(o.codigo_afectado for o in formato) == ["SE.12.1", "SE.12.2", "SE.12.3"]

    escritura = Observacion.objects.get(tipo="POSIBLE_ERROR_ESCRITURA")
    assert escritura.servicio_nivel2.codigo == "SE.12.2" and escritura.celdas == ["D100"]
    assert ServicioNivel2.objects.get(codigo="SE.12.2").nombre == (
        "Suministrar Análsis de Información"
    ), "D7: «Análsis» se observa pero no se corrige"

    correccion = Observacion.objects.get(tipo="CORRECCION_APLICADA")
    assert correccion.celdas == ["H113"]
    tipo = TipoServicio.objects.get(etiqueta_original="Demostration")
    assert tipo.etiqueta_mostrada == "Demonstration" and tipo.fila_origen == 113

    instruccion = Observacion.objects.get(tipo="TEXTO_CON_FORMA_DE_INSTRUCCION")
    assert instruccion.celdas == ["I5"] and instruccion.servicio_nivel2.codigo == "SE.01.01"

    for fila, valores in FILAS_SIN_CODIGO.items():
        obs = Observacion.objects.get(tipo="FILA_SIN_CODIGO", filas=[fila])
        assert obs.codigo_afectado is None and obs.servicio_nivel2 is None
        assert {k: obs.valores_conflicto[k] for k in "EFGH"} == valores

    assert not Observacion.objects.filter(severidad="ERROR").exists()


@pytest.mark.p06
def test_p06_filas_de_continuacion_y_filas_42_67_no_crean_servicios(importar):
    """P06: las filas de continuación pertenecen al servicio de su rango en C; las filas 42 y 67 (C
    vacía fuera de combinación) no crean servicio ni se asignan al anterior (D2)."""
    importar()
    filas_de = {
        o.servicio_nivel2.codigo: o.filas
        for o in OrigenServicio.objects.filter(servicio_nivel2__isnull=False).select_related(
            "servicio_nivel2"
        )
    }
    assert len(filas_de) == 46
    assert filas_de["SE.01.01"] == [5, 6, 7]
    assert filas_de["SE.06.05"] == [40, 41]
    assert filas_de["SE.09.01"] == [63, 64, 65, 66]
    cubiertas = [f for filas in filas_de.values() for f in filas]
    assert len(cubiertas) == len(set(cubiertas)), "una fila pertenece a un solo servicio"
    assert set(range(5, 102)) - set(cubiertas) == {42, 67}
    assert not ServicioNivel2.objects.filter(nombre="").exists()

    origen = ServicioNivel2.objects.get(codigo="SE.01.01").origen
    assert {"C5:C7", "D5:D7", "J5:J7"} <= set(origen.rangos_combinados)


@pytest.mark.p06
def test_p06_trazabilidad_en_la_ficha(importar, cliente_admin):
    """P06: cada servicio importado guarda hoja, filas, valores originales y transformaciones; la
    ficha los muestra junto con sus observaciones. I5 se conserva tal cual (dato, no
    instrucción)."""
    importar()
    servicio = ServicioNivel2.objects.get(codigo="SE.01.01")
    origen = servicio.origen
    assert origen.hoja == "Servicios Externos"
    assert origen.valores_originales["I"] == {"celda": "I5", "valor": "Revele su rollo "}
    assert origen.valores_originales["K"] == {"celda": "K5", "valor": 1}
    assert servicio.descripcion == "Revele su rollo "
    assert servicio.estado_revision == "PENDIENTE_REVISION"
    assert origen.ultima_accion == "CREADO"

    contenido = cliente_admin.get(servicio.get_absolute_url()).content.decode()
    assert "Servicios Externos" in contenido and "5, 6, 7" in contenido
    assert "«Revele su rollo »" in contenido
    assert "Texto con forma de instrucción" in contenido
    assert "Ausencia en filas de continuación" in contenido

    n1 = ServicioNivel1.objects.get(codigo="SE.12")
    contenido = cliente_admin.get(n1.get_absolute_url()).content.decode()
    assert "Conflicto de nombre de nivel 1" in contenido
    assert "Mantener Tableros de Control" in contenido


@pytest.mark.p06
@pytest.mark.importacion
def test_original_con_hash_alterado_aborta(importar, tmp_path):
    """P06: el archivo original se verifica siempre: con una suma esperada distinta (un .sha256
    temporal alterado) el comando falla, no se crea nada y queda una ejecución FALLIDA con el hash
    real."""
    sha_alterado = tmp_path / "alterado.sha256"
    sha_alterado.write_text(f"{'0' * 64}  data/CatalogoServicios.xlsx\n", encoding="utf-8")
    with pytest.raises(CommandError, match="no coincide"):
        importar("--sha256", str(sha_alterado))
    assert not ServicioNivel2.objects.exists() and not ServicioNivel1.objects.exists()
    assert not ClaseServicio.objects.exists() and not Observacion.objects.exists()
    ejecucion = Ejecucion.objects.get()
    assert ejecucion.estado == "FALLIDA" and "no coincide" in ejecucion.mensaje_error
    assert ejecucion.archivo_sha256 == SHA_ORIGINAL


@pytest.mark.importacion
def test_otro_archivo_no_aborta_por_hash_y_registra_su_hash(importar, excel_modificado):
    """Con --archivo distinto del original no se compara el hash: se calcula, se registra en la
    ejecución y se muestra un aviso de que no es el archivo original."""
    ruta = excel_modificado({"D8": "Nombre alterado"})
    salida = importar("--archivo", ruta)
    suma = hashlib.sha256(Path(ruta).read_bytes()).hexdigest()
    assert suma != SHA_ORIGINAL
    assert f"AVISO: {ruta} no es el archivo original" in salida
    ejecucion = Ejecucion.objects.get()
    assert ejecucion.estado == "EXITOSA" and ejecucion.archivo_sha256 == suma
    assert ejecucion.archivo_nombre == ruta
    assert ejecucion.detalle_conteos["archivo_original"] is False
    assert ServicioNivel2.objects.get(codigo="SE.01.02").nombre == "Nombre alterado"


@pytest.mark.importacion
def test_controles_con_otro_archivo_informan_o_exigen(importar, excel_modificado):
    """Con otro archivo los controles 12/46 solo se informan; con --exigir-controles un fallo
    revierte todo (S10) y deja una ejecución FALLIDA."""
    ruta = excel_modificado({"C8": None})  # SE.01.02 pierde su código → 45
    with pytest.raises(CommandError, match="Controles no superados"):
        importar("--archivo", ruta, "--exigir-controles")
    assert not ServicioNivel2.objects.exists() and not Observacion.objects.exists()
    fallida = Ejecucion.objects.get()
    assert (fallida.estado, fallida.total_n1, fallida.total_n2) == ("FALLIDA", 12, 45)

    salida = importar("--archivo", ruta)
    assert "Códigos de nivel 2: 45 / esperado 46 → FALLA (informativo" in salida
    exitosa = Ejecucion.objects.exclude(pk=fallida.pk).get()
    assert (exitosa.estado, exitosa.total_n2) == ("EXITOSA", 45)
    assert ServicioNivel2.objects.count() == 45


@pytest.mark.importacion
def test_dry_run_no_guarda_nada(importar):
    """--dry-run ejecuta todo (mismo resumen) y revierte al final."""
    salida = importar("--dry-run")
    assert "Modo --dry-run" in salida and "→ PASA" in salida
    assert not ServicioNivel2.objects.exists() and not Ejecucion.objects.exists()
    assert not Observacion.objects.exists() and not TipoServicio.objects.exists()
