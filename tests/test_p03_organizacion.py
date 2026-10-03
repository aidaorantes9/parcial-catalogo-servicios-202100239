"""P03 (organización): el usuario de consulta lee la estructura pero no la modifica.

Rechazo en el servidor (403) en toda escritura, aunque se haga la petición directa.
"""

import pytest
from django.urls import reverse

from organizacion.models import Area, Departamento, Empresa, Puesto, Seccion

pytestmark = [pytest.mark.p03, pytest.mark.django_db]


@pytest.fixture
def registros(puesto):
    seccion = puesto.seccion
    departamento = seccion.departamento
    area = departamento.area
    return {
        "empresa": (area.empresa, {"codigo": "N", "nombre": "N"}),
        "area": (area, {"empresa": area.empresa.pk, "codigo": "N", "nombre": "N"}),
        "departamento": (departamento, {"area": area.pk, "codigo": "N", "nombre": "N"}),
        "seccion": (seccion, {"departamento": departamento.pk, "codigo": "N", "nombre": "N"}),
        "puesto": (puesto, {"seccion": seccion.pk, "codigo": "N", "nombre": "N"}),
    }


def test_consulta_lee_listados_y_detalles(cliente_consulta, registros, consulta):
    """P03: CONSULTA obtiene 200 en listados y detalles de las cinco entidades, sin botones de
    escritura ni hashes."""
    for nombre, (registro, _) in registros.items():
        for url in [
            reverse(f"organizacion:{nombre}_lista"),
            reverse(f"organizacion:{nombre}_detalle", args=[registro.pk]),
        ]:
            respuesta = cliente_consulta.get(url)
            assert respuesta.status_code == 200, url
            contenido = respuesta.content.decode()
            assert "Desactivar" not in contenido and "Editar" not in contenido, url
            assert "argon2" not in contenido and consulta.password not in contenido, url


def test_consulta_recibe_403_en_toda_escritura(cliente_consulta, registros):
    """P03: crear, editar, desactivar y reactivar por POST directo → 403 y nada cambia; GET de
    los formularios también → 403."""
    for nombre, (registro, datos) in registros.items():
        crear = reverse(f"organizacion:{nombre}_crear")
        editar = reverse(f"organizacion:{nombre}_editar", args=[registro.pk])
        for url in [crear, editar]:
            assert cliente_consulta.get(url).status_code == 403, url
            assert cliente_consulta.post(url, datos).status_code == 403, url
        for accion in ["desactivar", "reactivar"]:
            url = reverse(f"organizacion:{nombre}_{accion}", args=[registro.pk])
            assert cliente_consulta.post(url).status_code == 403, url

    for modelo in (Empresa, Area, Departamento, Seccion, Puesto):
        assert not modelo.objects.filter(codigo="N").exists()
        assert not modelo.objects.filter(activo=False).exists()


def test_reactivar_por_consulta_no_cambia_registro_inactivo(cliente_consulta, puesto):
    """P03: un registro inactivo sigue inactivo tras un POST de reactivación de CONSULTA."""
    otro = Puesto.objects.create(seccion=puesto.seccion, codigo="X", nombre="X", activo=False)
    url = reverse("organizacion:puesto_reactivar", args=[otro.pk])
    assert cliente_consulta.post(url).status_code == 403
    otro.refresh_from_db()
    assert otro.activo is False


def test_sin_sesion_redirige_al_login(client, puesto):
    """P03: sin sesión, listados y escrituras redirigen al inicio de sesión."""
    for url in [
        reverse("organizacion:empresa_lista"),
        reverse("organizacion:puesto_detalle", args=[puesto.pk]),
    ]:
        respuesta = client.get(url)
        assert respuesta.status_code == 302 and reverse("cuentas:entrar") in respuesta.url
    respuesta = client.post(reverse("organizacion:empresa_crear"), {"codigo": "N", "nombre": "N"})
    assert respuesta.status_code == 302
    assert not Empresa.objects.filter(codigo="N").exists()


def test_inicio_muestra_conteos_de_activos(cliente_consulta, puesto):
    """P03: la página de inicio (lectura) muestra conteos de registros activos."""
    Empresa.objects.create(codigo="INACT", nombre="Inactiva", activo=False)
    respuesta = cliente_consulta.get(reverse("inicio"))
    assert respuesta.status_code == 200
    conteos = {nombre: total for nombre, total, _ in respuesta.context["conteos"]}
    assert conteos == {
        "Empresas": 1,
        "Áreas": 1,
        "Departamentos": 1,
        "Secciones": 1,
        "Puestos": 1,
        "Usuarios": 1,
    }
