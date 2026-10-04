"""Pantalla de historial de importaciones: solo lectura y solo ADMIN."""

import pytest
from django.urls import reverse

from importacion.models import Ejecucion

pytestmark = [pytest.mark.importacion, pytest.mark.django_db]


@pytest.mark.p07
def test_admin_ve_historial_y_observaciones(importar, cliente_admin):
    """P07 (resultado trazable): el administrador ve las ejecuciones (enlazadas desde el menú) y,
    en el detalle, los conteos y las observaciones emitidas con enlace al servicio."""
    importar()
    importar()
    lista = cliente_admin.get(reverse("importacion:ejecucion_lista"))
    assert lista.status_code == 200
    contenido = lista.content.decode()
    assert f'href="{reverse("importacion:ejecucion_lista")}"' in contenido  # menú
    assert contenido.count("Exitosa") == 2

    segunda = Ejecucion.objects.order_by("pk").last()
    detalle = cliente_admin.get(reverse("importacion:ejecucion_detalle", args=[segunda.pk]))
    contenido = detalle.content.decode()
    assert "Servicios de nivel 2" in contenido and "PASA" in contenido
    assert "Conflicto de nombre de nivel 1" in contenido and "Fila sin código" in contenido
    assert "SE.12.3" in contenido
    assert "nueva" not in contenido.split("Observaciones emitidas")[1].split("</thead>")[1]


@pytest.mark.p03
def test_consulta_y_anonimo_no_acceden(importar, client, cliente_consulta):
    """P03: el rol consulta recibe 403 en el historial de importaciones y no lo ve en el menú; sin
    sesión se redirige al login."""
    importar()
    pk = Ejecucion.objects.get().pk
    for url in (
        reverse("importacion:ejecucion_lista"),
        reverse("importacion:ejecucion_detalle", args=[pk]),
    ):
        assert cliente_consulta.get(url).status_code == 403
    contenido = cliente_consulta.get(reverse("inicio")).content.decode()
    assert reverse("importacion:ejecucion_lista") not in contenido
    client.logout()
    respuesta = client.get(reverse("importacion:ejecucion_lista"))
    assert respuesta.status_code == 302 and "/entrar/" in respuesta["Location"]


def test_historial_es_solo_lectura(importar, cliente_admin):
    """El historial de importaciones no acepta POST (405): es solo lectura."""
    importar()
    pk = Ejecucion.objects.get().pk
    url = reverse("importacion:ejecucion_detalle", args=[pk])
    assert cliente_admin.post(url).status_code == 405
    assert cliente_admin.post(reverse("importacion:ejecucion_lista")).status_code == 405
