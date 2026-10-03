"""P09: crear o editar un servicio con mínimo mayor que máximo.

La validación del formulario impide guardar y la restricción CHECK de la base también lo impide.
Un dato ausente se guarda como NULL (nunca 0 ni cadena vacía) y se muestra como «Sin dato».
"""

import re
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from catalogo.models import ServicioNivel2

pytestmark = [pytest.mark.p09, pytest.mark.django_db]

CREAR = "catalogo:servicionivel2_crear"
EDITAR = "catalogo:servicionivel2_editar"


def _valor_en_ficha(contenido, etiqueta):
    """Texto del <dd> que sigue al <dt> con la etiqueta dada."""
    encontrado = re.search(rf"<dt>{re.escape(etiqueta)}</dt>\s*<dd>(.*?)</dd>", contenido, re.S)
    assert encontrado, etiqueta
    return encontrado.group(1).strip()


def _errores(respuesta, campo):
    assert respuesta.status_code == 200
    return " ".join(respuesta.context["form"].errors.get(campo, []))


def test_crear_con_minimo_mayor_que_maximo_se_rechaza(cliente_admin, datos_servicio):
    """P09: al crear, mínimo 10 y máximo 5 → error comprensible y no se guarda."""
    respuesta = cliente_admin.post(reverse(CREAR), datos_servicio(minimo="10", maximo="5"))
    assert "El mínimo (10) no puede ser mayor que el máximo (5)" in _errores(respuesta, "maximo")
    assert not ServicioNivel2.objects.exists()


def test_editar_con_minimo_mayor_que_maximo_se_rechaza(
    cliente_admin, crear_servicio, datos_servicio
):
    """P09: al editar, mínimo 24 y máximo 12 → error y el registro conserva sus valores."""
    servicio = crear_servicio("T.01.01", minimo=Decimal("12"), maximo=Decimal("24"))
    respuesta = cliente_admin.post(
        reverse(EDITAR, args=[servicio.pk]), datos_servicio("T.01.01", minimo="24", maximo="12")
    )
    assert "no puede ser mayor que el máximo" in _errores(respuesta, "maximo")
    servicio.refresh_from_db()
    assert (servicio.minimo, servicio.maximo) == (Decimal("12"), Decimal("24"))


def test_restriccion_de_la_base_impide_minimo_mayor_que_maximo(crear_servicio):
    """P09: aunque se salte la validación del servidor (ORM directo), el CHECK
    ck_n2_minimo_le_maximo de PostgreSQL rechaza la fila, al crear y al actualizar."""
    with pytest.raises(IntegrityError, match="ck_n2_minimo_le_maximo"), transaction.atomic():
        crear_servicio("T.01.01", minimo=Decimal("5"), maximo=Decimal("1"))

    servicio = crear_servicio("T.01.02", minimo=Decimal("1"), maximo=Decimal("5"))
    with pytest.raises(IntegrityError, match="ck_n2_minimo_le_maximo"), transaction.atomic():
        ServicioNivel2.objects.filter(pk=servicio.pk).update(minimo=Decimal("9"))
    servicio.refresh_from_db()
    assert servicio.minimo == Decimal("1")


def test_minimo_igual_a_maximo_y_un_solo_extremo_se_permiten(cliente_admin, datos_servicio):
    """P09: mínimo = máximo, solo mínimo o solo máximo son válidos."""
    casos = [("T.01.01", "7", "7"), ("T.01.02", "3", ""), ("T.01.03", "", "100")]
    for codigo, minimo, maximo in casos:
        respuesta = cliente_admin.post(
            reverse(CREAR), datos_servicio(codigo, minimo=minimo, maximo=maximo)
        )
        assert respuesta.status_code == 302, codigo
    valores = dict(ServicioNivel2.objects.values_list("codigo", "minimo"))
    assert valores == {"T.01.01": Decimal("7"), "T.01.02": Decimal("3"), "T.01.03": None}
    assert ServicioNivel2.objects.get(codigo="T.01.02").maximo is None


def test_campos_vacios_quedan_null_y_cero_se_conserva(cliente_admin, datos_servicio):
    """P09: mínimo y máximo vacíos → NULL (no 0); descripción, métrica y ACTIVO vacíos → NULL
    (no cadena vacía); un 0 escrito por el usuario se guarda como 0."""
    datos = datos_servicio("T.01.01", descripcion="   ", metrica="", activo_excel="")
    assert cliente_admin.post(reverse(CREAR), datos).status_code == 302
    servicio = ServicioNivel2.objects.get(codigo="T.01.01")
    assert servicio.minimo is None and servicio.maximo is None
    assert servicio.descripcion is None and servicio.metrica is None
    assert servicio.activo_excel is None
    assert servicio.clase_id is None and servicio.seccion_responsable_id is None

    datos = datos_servicio("T.01.02", minimo="0", maximo="0")
    assert cliente_admin.post(reverse(CREAR), datos).status_code == 302
    cero = ServicioNivel2.objects.get(codigo="T.01.02")
    assert cero.minimo == Decimal("0") and cero.maximo == Decimal("0")


def test_ficha_muestra_sin_dato_y_desconocido_nunca_cero(cliente_consulta, crear_servicio):
    """P09: en la ficha, NULL se muestra como «Sin dato» (ACTIVO como «Desconocido») y un 0
    real como 0."""
    vacio = crear_servicio("T.01.01")
    contenido = cliente_consulta.get(vacio.get_absolute_url()).content.decode()
    etiquetas = ["Mínimo", "Máximo", "Métrica", "Descripción", "Clase de servicio", "Criticidad"]
    for etiqueta in etiquetas + ["Tipo de servicio"]:
        assert _valor_en_ficha(contenido, etiqueta) == "Sin dato", etiqueta
    assert _valor_en_ficha(contenido, "ACTIVO (Excel)") == "Desconocido"
    assert _valor_en_ficha(contenido, "Sección responsable") == "Sin asignar"

    cero = crear_servicio("T.01.02", minimo=Decimal("0"), maximo=Decimal("1.5000"))
    contenido = cliente_consulta.get(cero.get_absolute_url()).content.decode()
    assert _valor_en_ficha(contenido, "Mínimo") == "0"
    assert _valor_en_ficha(contenido, "Máximo") == "1.5"


def test_editar_conserva_valor_original_no_reconocido_y_espacios(
    cliente_admin, crear_servicio, datos_servicio
):
    """P09/D8: al editar, un ACTIVO original distinto de S/N se ofrece y se conserva, y la
    descripción no se recorta (los datos originales no se alteran sin que el usuario lo haga)."""
    servicio = crear_servicio("T.01.01", activo_excel="Si ", descripcion="Texto con espacio ")
    url = reverse(EDITAR, args=[servicio.pk])
    formulario = cliente_admin.get(url).context["form"]
    assert ("Si ", "'Si ' (valor original no reconocido)") in formulario.fields[
        "activo_excel"
    ].choices
    assert formulario.initial["activo_excel"] == "Si "

    datos = datos_servicio(
        "T.01.01", nombre="Renombrado", activo_excel="Si ", descripcion="Texto con espacio "
    )
    assert cliente_admin.post(url, datos).status_code == 302
    servicio.refresh_from_db()
    assert servicio.activo_excel == "Si " and servicio.descripcion == "Texto con espacio "
