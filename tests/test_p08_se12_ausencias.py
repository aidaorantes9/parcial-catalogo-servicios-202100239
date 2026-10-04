"""P08: SE.12 y atributos ausentes → política de conflicto aplicada y ausencias conservadas.

Incluye la regla de valores fuera de lista con un Excel generado en la prueba (copia del original
en un directorio temporal; el original nunca se modifica).
"""

from decimal import Decimal

import pytest

from catalogo.models import ClaseServicio, Criticidad, ServicioNivel1, ServicioNivel2, TipoServicio
from importacion.models import Observacion

pytestmark = [pytest.mark.django_db]

CAMPOS_AUSENTES = (
    "activo_excel",
    "clase",
    "criticidad",
    "tipo",
    "descripcion",
    "metrica",
    "minimo",
    "maximo",
)


@pytest.mark.p08
def test_p08_se12_nombre_canonico_y_evidencia(importar):
    """P08 (D3): un solo SE.12 con nombre «Suministrar Analitica» (B99), el nombre alternativo de
    B100 conservado en el origen y en la observación, y estado PENDIENTE_REVISION."""
    importar()
    se12 = ServicioNivel1.objects.get(codigo="SE.12")
    assert ServicioNivel1.objects.filter(codigo="SE.12").count() == 1
    assert se12.nombre == "Suministrar Analitica"
    assert se12.estado_revision == "PENDIENTE_REVISION"
    originales = se12.origen.valores_originales
    assert originales["B"] == {"celda": "B99", "valor": "Suministrar Analitica"}
    assert originales["B (B100)"] == {"celda": "B100", "valor": "Mantener Tableros de Control"}
    assert se12.origen.filas == [99, 100]
    obs = Observacion.objects.get(tipo="CONFLICTO_NOMBRE_N1", servicio_nivel1=se12)
    assert obs.valores_conflicto == {
        "B99": "Suministrar Analitica",
        "B100": "Mantener Tableros de Control",
    }
    assert sorted(se12.servicios_nivel2.values_list("codigo", flat=True)) == [
        "SE.12.1",
        "SE.12.2",
        "SE.12.3",
    ]


@pytest.mark.p08
def test_p08_filas_99_a_101_con_null_y_pendiente_revision(importar):
    """P08 (D4–D6): SE.12.1–SE.12.3 conservan su código como texto, quedan con todos los
    atributos en NULL (nunca 0 ni cadena vacía) y PENDIENTE_REVISION; SE.12.3 pertenece a SE.12
    por prefijo."""
    importar()
    for codigo in ("SE.12.1", "SE.12.2", "SE.12.3"):
        servicio = ServicioNivel2.objects.get(codigo_original=codigo)
        assert servicio.codigo == codigo
        assert servicio.nivel1.codigo == "SE.12"
        assert servicio.estado_revision == "PENDIENTE_REVISION"
        for campo in CAMPOS_AUSENTES:
            assert getattr(servicio, campo) is None, f"{codigo}.{campo}"
    origen = ServicioNivel2.objects.get(codigo="SE.12.3").origen
    assert {"campo": "nivel1", "regla": "padre_por_prefijo SE.12"} in origen.transformaciones
    assert origen.valores_originales["A"] == {"celda": "A101", "valor": None}
    assert not ServicioNivel2.objects.filter(minimo=0).exists()
    assert not ServicioNivel2.objects.filter(maximo=0).exists()


@pytest.mark.p08
def test_p08_activo_excel_conserva_el_texto_original(importar):
    """P08 (D8): `activo_excel` guarda el texto de la columna E; S/N tal cual y vacío como NULL.
    K/L solo tienen valor donde el Excel lo tiene."""
    importar()
    assert ServicioNivel2.objects.get(codigo="SE.05.01").activo_excel == "N"
    assert ServicioNivel2.objects.filter(activo_excel="S").count() == 42
    assert ServicioNivel2.objects.filter(activo_excel__isnull=True).count() == 3
    assert not ServicioNivel2.objects.filter(activo_excel="").exists()
    limites = {
        s.codigo: (s.minimo, s.maximo)
        for s in ServicioNivel2.objects.exclude(minimo__isnull=True, maximo__isnull=True)
    }
    assert limites == {
        "SE.01.01": (Decimal("1"), Decimal("100")),  # K5, L5
        "SE.05.02": (Decimal("12"), Decimal("24")),  # K25, L25
    }


@pytest.mark.p08
def test_p08_valores_fuera_de_lista_y_activo_no_reconocido(
    importar, excel_modificado, cliente_admin
):
    """P08: valor fuera de lista en F, G y H y ACTIVO distinto de S/N (Excel generado en la prueba):
    VALOR_NO_RECONOCIDO con columna, fila y valor; FK en NULL; ningún valor nuevo en los catálogos;
    original conservado en el origen y visible en la ficha; ACTIVO guardado tal cual."""
    ruta = excel_modificado({"F8": "BAJO DEMANDA", "G9": "Media", "H10": "Backend", "E11": "Si"})
    salida = importar("--archivo", ruta, "--exigir-controles")
    assert "→ PASA" in salida and "FALLA" not in salida

    assert (ClaseServicio.objects.count(), Criticidad.objects.count()) == (2, 5)
    assert TipoServicio.objects.count() == 11

    casos = {
        "F": ("SE.01.02", 8, "BAJO DEMANDA", "clase"),
        "G": ("SE.01.03", 9, "Media", "criticidad"),
        "H": ("SE.02.01", 10, "Backend", "tipo"),
    }
    for columna, (codigo, fila, valor, campo) in casos.items():
        servicio = ServicioNivel2.objects.get(codigo=codigo)
        assert servicio.origen.filas == [fila]
        assert getattr(servicio, campo) is None
        assert servicio.estado_revision == "PENDIENTE_REVISION"
        assert servicio.origen.valores_originales[columna]["valor"] == valor
        obs = Observacion.objects.get(tipo="VALOR_NO_RECONOCIDO", servicio_nivel2=servicio)
        assert obs.valores_conflicto == {"columna": columna, "fila": fila, "valor": valor}

    activo = ServicioNivel2.objects.get(codigo="SE.02.02")
    assert activo.activo_excel == "Si" and activo.estado_revision == "PENDIENTE_REVISION"
    obs = Observacion.objects.get(tipo="VALOR_NO_RECONOCIDO", servicio_nivel2=activo)
    assert obs.valores_conflicto == {"columna": "E", "fila": 11, "valor": "Si"}

    ficha = cliente_admin.get(ServicioNivel2.objects.get(codigo="SE.01.02").get_absolute_url())
    contenido = ficha.content.decode()
    assert "Sin valor reconocido — original en Excel" in contenido
    assert "«BAJO DEMANDA»" in contenido
