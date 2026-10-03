"""P03 (catálogo): el usuario de consulta lee el catálogo pero no lo modifica.

Lee listados y fichas (200, sin botones de escritura ni hashes) y recibe 403 en el servidor en toda
escritura, aunque haga la petición directa.
"""

import pytest
from django.urls import reverse

from catalogo.models import ClaseServicio, Criticidad, ServicioNivel1, ServicioNivel2, TipoServicio

pytestmark = [pytest.mark.p03, pytest.mark.django_db]


@pytest.fixture
def registros(catalogo, crear_servicio, puesto, consulta):
    servicio = crear_servicio(
        "T.01.01", seccion_responsable=puesto.seccion, usuario_responsable=consulta
    )
    datos_valor = {"codigo": "NUEVO", "etiqueta": "Nuevo", "etiqueta_mostrada": "X", "orden": 9}
    return {
        "servicionivel2": (
            servicio,
            {"nivel1": catalogo.nivel1.pk, "codigo": "NUEVO", "nombre": "N", "activo_excel": ""},
        ),
        "servicionivel1": (catalogo.nivel1, {"codigo": "NUEVO", "nombre": "N"}),
        "claseservicio": (catalogo.clase, datos_valor),
        "criticidad": (catalogo.criticidad, datos_valor),
        "tiposervicio": (catalogo.tipo, datos_valor),
    }


def test_consulta_lee_listados_y_fichas(cliente_consulta, registros, consulta):
    """P03: CONSULTA obtiene 200 en el índice, los listados y las fichas de las cinco entidades,
    sin botones de escritura ni hashes de contraseña."""
    assert cliente_consulta.get(reverse("catalogo:indice")).status_code == 200
    for nombre, (registro, _) in registros.items():
        for url in [
            reverse(f"catalogo:{nombre}_lista"),
            reverse(f"catalogo:{nombre}_detalle", args=[registro.pk]),
        ]:
            respuesta = cliente_consulta.get(url)
            assert respuesta.status_code == 200, url
            contenido = respuesta.content.decode()
            for texto in ["Desactivar", "Editar", "Reactivar", reverse(f"catalogo:{nombre}_crear")]:
                assert texto not in contenido, (url, texto)
            assert "argon2" not in contenido and consulta.password not in contenido, url


def test_consulta_recibe_403_en_toda_escritura(cliente_consulta, registros):
    """P03: crear y editar (GET y POST), desactivar y reactivar (POST) → 403 y nada cambia."""
    for nombre, (registro, datos) in registros.items():
        crear = reverse(f"catalogo:{nombre}_crear")
        editar = reverse(f"catalogo:{nombre}_editar", args=[registro.pk])
        for url in [crear, editar]:
            assert cliente_consulta.get(url).status_code == 403, url
            assert cliente_consulta.post(url, datos).status_code == 403, url
        for accion in ["desactivar", "reactivar"]:
            url = reverse(f"catalogo:{nombre}_{accion}", args=[registro.pk])
            assert cliente_consulta.post(url).status_code == 403, url

    for modelo in (ServicioNivel1, ServicioNivel2, ClaseServicio, Criticidad, TipoServicio):
        assert not modelo.objects.filter(codigo="NUEVO").exists(), modelo
        assert not modelo.objects.filter(activo=False).exists(), modelo
    servicio = registros["servicionivel2"][0]
    servicio.refresh_from_db()
    assert servicio.codigo == "T.01.01"


def test_reactivar_por_consulta_no_cambia_servicio_dado_de_baja(cliente_consulta, crear_servicio):
    """P03: un servicio dado de baja sigue así tras un POST de reactivación de CONSULTA."""
    servicio = crear_servicio("T.01.09", activo=False)
    url = reverse("catalogo:servicionivel2_reactivar", args=[servicio.pk])
    assert cliente_consulta.post(url).status_code == 403
    servicio.refresh_from_db()
    assert servicio.activo is False


def test_sin_sesion_redirige_al_login(client, crear_servicio, catalogo):
    """P03: sin sesión, listados, fichas y escrituras del catálogo redirigen al login."""
    servicio = crear_servicio("T.01.01")
    for url in [reverse("catalogo:servicionivel2_lista"), servicio.get_absolute_url()]:
        respuesta = client.get(url)
        assert respuesta.status_code == 302 and reverse("cuentas:entrar") in respuesta.url
    datos = {"codigo": "NUEVO", "nombre": "N", "estado_revision": "SIN_OBSERVACIONES"}
    assert client.post(reverse("catalogo:servicionivel1_crear"), datos).status_code == 302
    assert not ServicioNivel1.objects.filter(codigo="NUEVO").exists()
