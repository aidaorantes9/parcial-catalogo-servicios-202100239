"""P04: crear una jerarquía y asignar un usuario.

Relaciones válidas y recuperables, creadas a través de las vistas como ADMIN.
"""

import pytest
from django.urls import reverse

from cuentas.models import Rol, Usuario
from organizacion.models import Area, Departamento, Empresa, Puesto, Seccion

pytestmark = [pytest.mark.p04, pytest.mark.django_db]

CLAVE = "Clave-Nueva-Segura-2026!"


def _crear(cliente, nombre_url, datos, modelo):
    respuesta = cliente.post(reverse(f"organizacion:{nombre_url}_crear"), datos)
    assert respuesta.status_code == 302, respuesta.context["form"].errors
    return modelo.objects.get(**datos)


def test_jerarquia_completa_y_usuario_desde_las_vistas(cliente_admin):
    """P04: Empresa → Área → Departamento → Sección → Puesto por POST, usuario en el puesto y
    recuperación de toda la ruta y de la empresa derivada."""
    empresa = _crear(cliente_admin, "empresa", {"codigo": "ACME", "nombre": "Acme S.A."}, Empresa)
    area = _crear(
        cliente_admin, "area", {"empresa": empresa.pk, "codigo": "TI", "nombre": "Tecnología"}, Area
    )
    departamento = _crear(
        cliente_admin,
        "departamento",
        {"area": area.pk, "codigo": "INF", "nombre": "Infraestructura"},
        Departamento,
    )
    seccion = _crear(
        cliente_admin,
        "seccion",
        {"departamento": departamento.pk, "codigo": "RED", "nombre": "Redes"},
        Seccion,
    )
    puesto = _crear(
        cliente_admin,
        "puesto",
        {"seccion": seccion.pk, "codigo": "ANA", "nombre": "Analista"},
        Puesto,
    )

    respuesta = cliente_admin.post(
        reverse("cuentas:usuario_crear"),
        {
            "username": "ana",
            "email": "ana@example.com",
            "nombre": "Ana Analista",
            "rol": Rol.CONSULTA,
            "puesto": puesto.pk,
            "password1": CLAVE,
            "password2": CLAVE,
        },
    )
    assert respuesta.status_code == 302

    usuario = Usuario.objects.get(username="ana")
    assert usuario.puesto == puesto
    assert usuario.empresa == empresa
    assert Puesto.con_jerarquia().get(pk=puesto.pk).ancestros() == [
        empresa,
        area,
        departamento,
        seccion,
    ]
    assert puesto.ruta == "ACME / TI / INF / RED / ANA — Analista"

    # El detalle del puesto muestra la ruta completa y sus usuarios con la empresa derivada.
    detalle = cliente_admin.get(reverse("organizacion:puesto_detalle", args=[puesto.pk]))
    assert detalle.status_code == 200
    assert [n for n, _ in detalle.context["ruta"]] == [empresa, area, departamento, seccion]
    assert [u for u, _ in detalle.context["usuarios"]] == [usuario]
    contenido = detalle.content.decode()
    assert "Acme S.A." in contenido and "ana" in contenido

    # El detalle de cada nivel lista a su hijo directo.
    for modelo, padre, hijo in [
        ("empresa", empresa, area),
        ("area", area, departamento),
        ("departamento", departamento, seccion),
        ("seccion", seccion, puesto),
    ]:
        detalle = cliente_admin.get(reverse(f"organizacion:{modelo}_detalle", args=[padre.pk]))
        assert [h for h, _ in detalle.context["hijos"]] == [hijo], modelo

    # El detalle y la lista de usuarios muestran la empresa derivada.
    detalle = cliente_admin.get(reverse("cuentas:usuario_detalle", args=[usuario.pk]))
    assert str(empresa) in detalle.content.decode()
    lista = cliente_admin.get(reverse("cuentas:usuario_lista"), {"q": "ana"})
    assert str(empresa) in lista.content.decode()


def test_listado_busqueda_filtros_y_paginacion(cliente_admin, puesto):
    """P04: listado con búsqueda por código o nombre, filtros por estado y padre y paginación."""
    empresa = puesto.seccion.departamento.area.empresa
    otra = Empresa.objects.create(codigo="OTRA", nombre="Otra empresa")
    for i in range(22):
        Area.objects.create(empresa=empresa, codigo=f"A{i:02d}", nombre=f"Área {i:02d}")
    Area.objects.create(empresa=otra, codigo="X1", nombre="Compras", activo=False)

    url = reverse("organizacion:area_lista")
    respuesta = cliente_admin.get(url)
    assert respuesta.context["is_paginated"] and len(respuesta.context["registros"]) == 20

    assert [a.codigo for a in cliente_admin.get(url, {"q": "compras"}).context["registros"]] == [
        "X1"
    ]
    assert [a.codigo for a in cliente_admin.get(url, {"q": "a07"}).context["registros"]] == ["A07"]
    inactivas = cliente_admin.get(url, {"estado": "inactivos"}).context["registros"]
    assert [a.codigo for a in inactivas] == ["X1"]
    de_otra = cliente_admin.get(url, {"padre": otra.pk}).context["registros"]
    assert [a.codigo for a in de_otra] == ["X1"]
    activas_emp = cliente_admin.get(url, {"padre": empresa.pk, "estado": "activos"})
    assert activas_emp.context["paginator"].count == 23  # 22 nuevas + «AR» del fixture.
    # La paginación conserva los filtros.
    assert "estado=activos" in activas_emp.context["filtros"]
