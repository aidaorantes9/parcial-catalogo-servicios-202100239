"""P05 (organización): código duplicado o referencia inexistente.

Rechazo con mensaje comprensible, validado en el servidor.
"""

import pytest
from django.urls import reverse

from organizacion.models import Area, Departamento, Empresa, Puesto, Seccion

pytestmark = [pytest.mark.p05, pytest.mark.django_db]


def _errores(respuesta, campo):
    assert respuesta.status_code == 200
    return " ".join(respuesta.context["form"].errors.get(campo, []))


@pytest.fixture
def area(puesto):
    return puesto.seccion.departamento.area


def test_codigo_duplicado_en_el_mismo_padre_se_rechaza(cliente_admin, area):
    """P05: un área con código repetido en la misma empresa se rechaza con mensaje."""
    datos = {"empresa": area.empresa.pk, "codigo": "AR", "nombre": "Repetida"}
    respuesta = cliente_admin.post(reverse("organizacion:area_crear"), datos)
    assert "ya está en uso" in _errores(respuesta, "codigo")
    assert Area.objects.filter(codigo="AR").count() == 1


def test_codigo_duplicado_en_cada_nivel(cliente_admin, puesto):
    """P05: la regla aplica a departamento, sección y puesto (dentro del padre) y a empresa
    (global); también al editar."""
    seccion = puesto.seccion
    departamento = seccion.departamento
    casos = [
        ("empresa", {"codigo": "EMP", "nombre": "Otra"}),
        ("departamento", {"area": departamento.area.pk, "codigo": "DP", "nombre": "X"}),
        ("seccion", {"departamento": departamento.pk, "codigo": "SC", "nombre": "X"}),
        ("puesto", {"seccion": seccion.pk, "codigo": "PU", "nombre": "X"}),
    ]
    for nombre_url, datos in casos:
        respuesta = cliente_admin.post(reverse(f"organizacion:{nombre_url}_crear"), datos)
        assert "ya está en uso" in _errores(respuesta, "codigo"), nombre_url

    otro = Puesto.objects.create(seccion=seccion, codigo="PU2", nombre="Otro")
    respuesta = cliente_admin.post(
        reverse("organizacion:puesto_editar", args=[otro.pk]),
        {"seccion": seccion.pk, "codigo": "PU", "nombre": "Otro"},
    )
    assert "ya está en uso" in _errores(respuesta, "codigo")
    otro.refresh_from_db()
    assert otro.codigo == "PU2"


def test_mismo_codigo_en_otro_padre_se_permite(cliente_admin, area):
    """P05: el mismo código de área en otra empresa sí se acepta."""
    otra = Empresa.objects.create(codigo="OTRA", nombre="Otra empresa")
    datos = {"empresa": otra.pk, "codigo": "AR", "nombre": "Área de otra empresa"}
    respuesta = cliente_admin.post(reverse("organizacion:area_crear"), datos)
    assert respuesta.status_code == 302
    assert Area.objects.filter(codigo="AR").count() == 2


def test_padre_inexistente_se_rechaza(cliente_admin):
    """P05: referencia a un padre que no existe (POST directo) → mensaje, sin crear nada."""
    for valor in ["999999", "abc"]:
        datos = {"empresa": valor, "codigo": "NUEVA", "nombre": "Huérfana"}
        respuesta = cliente_admin.post(reverse("organizacion:area_crear"), datos)
        assert "no existe" in _errores(respuesta, "empresa"), valor
    respuesta = cliente_admin.post(
        reverse("organizacion:area_crear"), {"codigo": "NUEVA", "nombre": "Sin padre"}
    )
    assert "obligatorio" in _errores(respuesta, "empresa")
    assert not Area.objects.filter(codigo="NUEVA").exists()


def test_padre_inactivo_se_rechaza_al_crear_y_al_cambiar(cliente_admin, puesto):
    """P05: no se asocia un registro nuevo a un padre inactivo ni se mueve a uno inactivo."""
    departamento = puesto.seccion.departamento
    inactivo = Departamento.objects.create(
        area=departamento.area, codigo="DPX", nombre="Inactivo", activo=False
    )
    respuesta = cliente_admin.post(
        reverse("organizacion:seccion_crear"),
        {"departamento": inactivo.pk, "codigo": "NUEVA", "nombre": "Nueva"},
    )
    assert "está inactivo" in _errores(respuesta, "departamento")
    assert not Seccion.objects.filter(codigo="NUEVA").exists()

    seccion = puesto.seccion
    respuesta = cliente_admin.post(
        reverse("organizacion:seccion_editar", args=[seccion.pk]),
        {"departamento": inactivo.pk, "codigo": seccion.codigo, "nombre": seccion.nombre},
    )
    assert "está inactivo" in _errores(respuesta, "departamento")
    seccion.refresh_from_db()
    assert seccion.departamento == departamento


def test_edicion_conserva_padre_que_se_desactivo_despues(cliente_admin):
    """P05: editar el nombre de un hijo inactivo cuyo padre ya está inactivo no exige cambiar de
    padre (solo se rechazan asociaciones nuevas)."""
    empresa = Empresa.objects.create(codigo="E2", nombre="Empresa 2")
    area = Area.objects.create(empresa=empresa, codigo="A2", nombre="Área 2", activo=False)
    Empresa.objects.filter(pk=empresa.pk).update(activo=False)
    respuesta = cliente_admin.post(
        reverse("organizacion:area_editar", args=[area.pk]),
        {"empresa": empresa.pk, "codigo": "A2", "nombre": "Área renombrada"},
    )
    assert respuesta.status_code == 302
    area.refresh_from_db()
    assert area.nombre == "Área renombrada"
