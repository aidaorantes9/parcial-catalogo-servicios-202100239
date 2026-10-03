"""P05 (organización): política D1 de desactivación y reactivación.

Desactivar con dependientes activos se rechaza y se listan; sin ellos se permite; reactivar con
padre inactivo se rechaza. Nunca hay borrado físico.
"""

import pytest
from django.urls import reverse

from organizacion.models import Area, Empresa, Puesto, Seccion

pytestmark = [pytest.mark.p05, pytest.mark.django_db]


def _url(modelo, accion, pk):
    return reverse(f"organizacion:{modelo}_{accion}", args=[pk])


def test_desactivar_con_hijos_activos_se_rechaza_y_lista_dependientes(cliente_admin, puesto):
    """P05/D1: una sección con un puesto activo no se desactiva; se muestra el puesto."""
    seccion = puesto.seccion
    otro = Puesto.objects.create(seccion=seccion, codigo="PU2", nombre="Otro puesto")
    Puesto.objects.create(seccion=seccion, codigo="PU3", nombre="Inactivo", activo=False)

    respuesta = cliente_admin.post(_url("seccion", "desactivar", seccion.pk))
    assert respuesta.status_code == 200
    assert [d for d, _ in respuesta.context["dependientes_bloqueo"]] == [puesto, otro]
    contenido = respuesta.content.decode()
    assert "No se puede desactivar" in contenido
    assert str(puesto) in contenido and str(otro) in contenido and "PU3" in contenido
    seccion.refresh_from_db()
    assert seccion.activo


def test_desactivar_puesto_con_usuarios_activos_se_rechaza(cliente_admin, admin, puesto):
    """P05/D1: un puesto con usuarios activos no se desactiva; se listan los usuarios."""
    respuesta = cliente_admin.post(_url("puesto", "desactivar", puesto.pk))
    assert [u for u, _ in respuesta.context["dependientes_bloqueo"]] == [admin]
    puesto.refresh_from_db()
    assert puesto.activo


def test_desactivar_sin_dependientes_activos_se_permite(cliente_admin, puesto):
    """P05/D1: un área cuyos departamentos están todos inactivos sí se desactiva (baja lógica:
    el registro sigue existiendo)."""
    empresa = puesto.seccion.departamento.area.empresa
    area = Area.objects.create(empresa=empresa, codigo="AR2", nombre="Área vacía")
    hoja = Area.objects.create(empresa=empresa, codigo="AR3", nombre="Con hijo inactivo")
    hoja.departamentos.create(codigo="D", nombre="Inactivo", activo=False)

    for registro in (area, hoja):
        respuesta = cliente_admin.post(_url("area", "desactivar", registro.pk))
        assert respuesta.status_code == 302
        registro.refresh_from_db()
        assert registro.activo is False


def test_reactivar_con_padre_inactivo_se_rechaza(cliente_admin):
    """P05/D1: no se reactiva un hijo bajo un padre inactivo; con el padre activo sí."""
    empresa = Empresa.objects.create(codigo="E2", nombre="Empresa 2")
    area = Area.objects.create(empresa=empresa, codigo="A2", nombre="Área 2", activo=False)
    cliente_admin.post(_url("empresa", "desactivar", empresa.pk))
    empresa.refresh_from_db()
    assert empresa.activo is False

    respuesta = cliente_admin.post(_url("area", "reactivar", area.pk), follow=True)
    mensajes = [str(m) for m in respuesta.context["messages"]]
    assert any("está inactivo" in m for m in mensajes), mensajes
    area.refresh_from_db()
    assert area.activo is False

    cliente_admin.post(_url("empresa", "reactivar", empresa.pk))
    cliente_admin.post(_url("area", "reactivar", area.pk))
    area.refresh_from_db()
    assert area.activo is True


def test_desactivar_por_niveles_de_abajo_hacia_arriba(cliente_admin, puesto, crear_usuario):
    """P05/D1: la rama completa se desactiva yendo de abajo hacia arriba, sin cascada."""
    usuario = crear_usuario("persona")
    cliente_admin.post(reverse("cuentas:usuario_desactivar", args=[usuario.pk]))
    # Queda el admin del fixture en el puesto: se mueve a otro puesto activo antes.
    otro = Puesto.objects.create(
        seccion=Seccion.objects.create(
            departamento=puesto.seccion.departamento, codigo="SC2", nombre="Otra"
        ),
        codigo="P",
        nombre="Puesto",
    )
    puesto.usuarios.filter(is_active=True).update(puesto=otro)

    assert cliente_admin.post(_url("puesto", "desactivar", puesto.pk)).status_code == 302
    assert cliente_admin.post(_url("seccion", "desactivar", puesto.seccion_id)).status_code == 302
    puesto.refresh_from_db()
    assert not puesto.activo and not puesto.seccion.activo


def test_no_hay_borrado_fisico_ni_cambio_de_estado_por_get(cliente_admin, puesto):
    """P05/D1: DELETE no está disponible y GET a desactivar no cambia nada (405)."""
    empresa = puesto.seccion.departamento.area.empresa
    assert cliente_admin.delete(_url("empresa", "detalle", empresa.pk)).status_code == 405
    assert cliente_admin.get(_url("empresa", "desactivar", empresa.pk)).status_code == 405
    assert Empresa.objects.filter(pk=empresa.pk, activo=True).exists()
