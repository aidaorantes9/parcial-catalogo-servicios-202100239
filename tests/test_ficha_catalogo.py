"""Catálogo: ficha de servicio, trazabilidad de importación, mapeo inicial y conteos del inicio.

Los registros de trazabilidad se crean en la prueba con valores controlados (no se lee el Excel):
solo se comprueba que la ficha los muestra y que la base aplica sus restricciones.
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from catalogo.models import TipoServicio
from importacion.models import Ejecucion, MapeoCorreccion, Observacion, OrigenServicio

pytestmark = [pytest.mark.catalogo, pytest.mark.django_db]

SHA = "0" * 64


@pytest.fixture
def ejecucion(db):
    return Ejecucion.objects.create(archivo_nombre="prueba.xlsx", archivo_sha256=SHA)


def test_ficha_muestra_todos_los_atributos_y_enlace_al_nivel1(
    cliente_consulta, catalogo, puesto, crear_servicio
):
    """La ficha de N2 muestra código, nombre, N1 con enlace, ACTIVO, clase, criticidad, tipo,
    descripción, métrica, mínimo, máximo, revisión, estado y responsables."""
    servicio = crear_servicio(
        "T.01.01",
        nombre="Servicio completo",
        activo_excel="N",
        clase=catalogo.clase,
        criticidad=catalogo.criticidad,
        tipo=catalogo.tipo,
        descripcion="Descripción de prueba",
        metrica="Porcentaje",
        minimo=Decimal("1"),
        maximo=Decimal("100"),
        estado_revision="REVISADO",
        seccion_responsable=puesto.seccion,
    )
    contenido = cliente_consulta.get(servicio.get_absolute_url()).content.decode()
    for texto in [
        "Servicio completo",
        f'href="{catalogo.nivel1.get_absolute_url()}"',
        "Clase A",
        "Media",
        "Tipo A",
        "Descripción de prueba",
        "Porcentaje",
        "<dd>100</dd>",
        "Revisado",
        "Sección responsable",
        str(puesto.seccion.nombre),
        "Registro creado en la aplicación",
    ]:
        assert texto in contenido, texto


def test_ficha_muestra_valores_originales_y_observaciones(
    cliente_consulta, catalogo, crear_servicio, ejecucion
):
    """Con origen de importación, la ficha muestra hoja, filas, valores originales (texto tal
    cual, como dato), el original no reconocido de una clase NULL y las observaciones de la
    última ejecución."""
    servicio = crear_servicio("T.01.01", estado_revision="PENDIENTE_REVISION")
    OrigenServicio.objects.create(
        servicio_nivel2=servicio,
        hoja="Servicios Externos",
        filas=[5, 6, 7],
        rangos_combinados=["C5:C7"],
        valores_originales={
            "C": {"celda": "C5", "valor": "T.01.01"},
            "F": {"celda": "F5", "valor": "Clase inexistente"},
            "I": {"celda": "I5", "valor": "Texto con forma de orden "},
        },
        primera_ejecucion=ejecucion,
        ultima_ejecucion=ejecucion,
        ultima_accion="CREADO",
    )
    anterior = Ejecucion.objects.create(archivo_nombre="viejo.xlsx", archivo_sha256=SHA)
    Observacion.objects.create(
        ejecucion=anterior,
        tipo="ATRIBUTOS_AUSENTES",
        servicio_nivel2=servicio,
        filas=[5],
        detalle="Observación de una ejecución anterior",
    )
    Observacion.objects.create(
        ejecucion=ejecucion,
        tipo="VALOR_NO_RECONOCIDO",
        servicio_nivel2=servicio,
        codigo_afectado="T.01.01",
        filas=[5],
        celdas=["F5"],
        detalle="La clase no coincide con la lista",
        valores_conflicto={"columna": "F", "fila": 5, "valor": "Clase inexistente"},
    )

    contenido = cliente_consulta.get(servicio.get_absolute_url()).content.decode()
    assert "Servicios Externos" in contenido and "5, 6, 7" in contenido and "C5:C7" in contenido
    assert "«Texto con forma de orden »" in contenido
    assert "Sin valor reconocido — original en Excel" in contenido
    assert "«Clase inexistente»" in contenido
    assert "Valor no reconocido" in contenido and "La clase no coincide" in contenido
    assert "Observación de una ejecución anterior" not in contenido
    assert "Pendiente de revisión" in contenido


def test_ficha_de_tipo_corregido_muestra_la_etiqueta_original(
    cliente_consulta, crear_valor, crear_servicio
):
    """D7: un tipo con etiqueta corregida muestra la corregida y la original de la lista."""
    tipo = crear_valor(TipoServicio, "DEMOSTRATION", "Demostration", 5, fila_origen=113)
    tipo.etiqueta_mostrada = "Demonstration"
    tipo.save()
    servicio = crear_servicio("T.01.01", tipo=tipo)
    contenido = cliente_consulta.get(servicio.get_absolute_url()).content.decode()
    assert "Demonstration" in contenido and "original en la lista: «Demostration»" in contenido


def test_valor_importado_no_permite_editar_la_etiqueta_mostrada(cliente_admin, crear_valor):
    """D7: en un valor importado del Excel solo se edita el orden; la etiqueta mostrada cambia
    solo con el mapeo de correcciones. En uno creado en la aplicación sí se edita."""
    importado = crear_valor(TipoServicio, "ONSITE", "Onsite", 1, fila_origen=112)
    propio = crear_valor(TipoServicio, "PROPIO", "Propio", 2)
    url = reverse("catalogo:tiposervicio_editar", args=[importado.pk])
    assert list(cliente_admin.get(url).context["form"].fields) == ["orden"]
    cliente_admin.post(url, {"etiqueta_mostrada": "Cambiada", "orden": 7})
    importado.refresh_from_db()
    assert (importado.etiqueta_mostrada, importado.orden) == ("Onsite", 7)

    url = reverse("catalogo:tiposervicio_editar", args=[propio.pk])
    assert cliente_admin.post(url, {"etiqueta_mostrada": "Propio 2", "orden": 2}).status_code == 302
    propio.refresh_from_db()
    assert (propio.etiqueta_original, propio.etiqueta_mostrada) == ("Propio", "Propio 2")


def test_ficha_nivel1_lista_sus_servicios(cliente_consulta, catalogo, crear_servicio):
    """La ficha del N1 lista sus N2 (activos y dados de baja) con enlace a cada ficha."""
    activo = crear_servicio("T.01.01")
    baja = crear_servicio("T.01.02", activo=False)
    contenido = cliente_consulta.get(catalogo.nivel1.get_absolute_url()).content.decode()
    for servicio in (activo, baja):
        assert f'href="{servicio.get_absolute_url()}"' in contenido
    assert "Dado de baja" in contenido


def test_mapeo_inicial_cargado_por_migracion(db):
    """D7: la migración de datos deja una sola regla activa, Demostration → Demonstration."""
    reglas = list(
        MapeoCorreccion.objects.values_list("ambito", "valor_original", "valor_corregido")
    )
    assert reglas == [("ETIQUETA_TIPO", "Demostration", "Demonstration")]
    assert MapeoCorreccion.objects.get().celda_origen == "H113"


def test_restricciones_de_trazabilidad(catalogo, crear_servicio, ejecucion):
    """El origen pertenece a exactamente un servicio y tiene al menos una fila; la ejecución
    exige un SHA-256 válido; el mapeo no admite un valor corregido igual al original."""
    servicio = crear_servicio("T.01.01")
    base = {
        "hoja": "Servicios Externos",
        "valores_originales": {},
        "primera_ejecucion": ejecucion,
        "ultima_ejecucion": ejecucion,
        "ultima_accion": "CREADO",
    }
    casos = [
        (lambda: OrigenServicio.objects.create(filas=[5], **base), "ck_origen_un_servicio"),
        (
            lambda: OrigenServicio.objects.create(
                servicio_nivel1=catalogo.nivel1, servicio_nivel2=servicio, filas=[5], **base
            ),
            "ck_origen_un_servicio",
        ),
        (
            lambda: OrigenServicio.objects.create(servicio_nivel2=servicio, filas=[], **base),
            "ck_origen_filas",
        ),
        (
            lambda: Ejecucion.objects.create(archivo_nombre="x", archivo_sha256="no-es-hash"),
            "ck_ejecucion_sha256",
        ),
        (
            lambda: MapeoCorreccion.objects.create(
                ambito="NOMBRE_N1", valor_original="A", valor_corregido="A", motivo="x"
            ),
            "ck_mapeocorreccion_cambia_valor",
        ),
    ]
    for crear, restriccion in casos:
        with pytest.raises(IntegrityError, match=restriccion), transaction.atomic():
            crear()


def test_inicio_y_menu_incluyen_el_catalogo(cliente_consulta, catalogo, crear_servicio):
    """El inicio muestra conteos del catálogo (activos de total) y el menú enlaza a él."""
    crear_servicio("T.01.01")
    crear_servicio("T.01.02", activo=False)
    respuesta = cliente_consulta.get(reverse("inicio"))
    conteos = {
        nombre: (activos, total)
        for nombre, activos, total, _ in respuesta.context["conteos_catalogo"]
    }
    assert conteos["Servicios de nivel 2"] == (1, 2)
    assert conteos["Servicios de nivel 1"] == (1, 1)
    assert conteos["Clases de servicio"] == (1, 1)
    contenido = respuesta.content.decode()
    assert reverse("catalogo:servicionivel2_lista") in contenido
    assert reverse("catalogo:indice") in contenido


def test_admin_abre_todas_las_pantallas_del_catalogo(cliente_admin, catalogo, crear_servicio):
    """Como ADMIN, índice, listados, fichas y formularios de alta y edición de las cinco
    entidades responden 200 y muestran las acciones de escritura."""
    servicio = crear_servicio("T.01.01", clase=catalogo.clase)
    registros = {
        "servicionivel2": servicio,
        "servicionivel1": catalogo.nivel1,
        "claseservicio": catalogo.clase,
        "criticidad": catalogo.criticidad,
        "tiposervicio": catalogo.tipo,
    }
    assert cliente_admin.get(reverse("catalogo:indice")).status_code == 200
    for nombre, registro in registros.items():
        for url in [
            reverse(f"catalogo:{nombre}_lista"),
            reverse(f"catalogo:{nombre}_crear"),
            reverse(f"catalogo:{nombre}_detalle", args=[registro.pk]),
            reverse(f"catalogo:{nombre}_editar", args=[registro.pk]),
        ]:
            assert cliente_admin.get(url).status_code == 200, url
        detalle = cliente_admin.get(reverse(f"catalogo:{nombre}_detalle", args=[registro.pk]))
        assert "Desactivar" in detalle.content.decode(), nombre
