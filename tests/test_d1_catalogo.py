"""P05 (catálogo): política D1 extendida al catálogo y a los responsables.

Se rechaza desactivar, listando los dependientes activos:
- una sección responsable de servicios activos;
- un servicio de nivel 1 con servicios de nivel 2 activos;
- un valor de clase, criticidad o tipo usado por servicios activos;
- un usuario que es usuario responsable de servicios activos (regla D1 + D9).
Sin dependientes activos se permite. Reactivar un servicio con referencias inactivas se rechaza.
Nada se desactiva en cascada ni se borra.
"""

import pytest
from django.urls import reverse

from catalogo.models import ServicioNivel1

pytestmark = [pytest.mark.p05, pytest.mark.django_db]


def _url(entidad, accion, pk):
    return reverse(f"catalogo:{entidad}_{accion}", args=[pk])


def _bloqueo(respuesta):
    assert respuesta.status_code == 200
    return [d for d, _ in respuesta.context["dependientes_bloqueo"]]


def test_seccion_responsable_de_servicios_activos_no_se_desactiva(
    cliente_admin, puesto, crear_servicio
):
    """P05/D1: una sección sin puestos pero responsable de un servicio activo no se desactiva;
    el bloqueo enlaza a la ficha del servicio. Con el servicio dado de baja, sí."""
    seccion = puesto.seccion.departamento.secciones.create(codigo="SC2", nombre="Sin puestos")
    servicio = crear_servicio("T.01.01", seccion_responsable=seccion)
    url = reverse("organizacion:seccion_desactivar", args=[seccion.pk])

    respuesta = cliente_admin.post(url)
    assert _bloqueo(respuesta) == [servicio]
    assert servicio.get_absolute_url() in respuesta.content.decode()
    seccion.refresh_from_db()
    assert seccion.activo

    assert cliente_admin.post(_url("servicionivel2", "desactivar", servicio.pk)).status_code == 302
    assert cliente_admin.post(url).status_code == 302
    seccion.refresh_from_db()
    servicio.refresh_from_db()
    assert seccion.activo is False
    # La asignación histórica se conserva en el servicio dado de baja (no hay cascada).
    assert servicio.seccion_responsable == seccion


def test_nivel1_con_servicios_activos_no_se_desactiva(cliente_admin, catalogo, crear_servicio):
    """P05/D1: un N1 con N2 activos no se desactiva y se listan; con N2 solo inactivos, sí."""
    activo = crear_servicio("T.01.01")
    crear_servicio("T.01.02", activo=False)
    url = _url("servicionivel1", "desactivar", catalogo.nivel1.pk)

    respuesta = cliente_admin.post(url)
    assert _bloqueo(respuesta) == [activo]
    assert "No se puede desactivar" in respuesta.content.decode()
    catalogo.nivel1.refresh_from_db()
    assert catalogo.nivel1.activo

    cliente_admin.post(_url("servicionivel2", "desactivar", activo.pk))
    assert cliente_admin.post(url).status_code == 302
    catalogo.nivel1.refresh_from_db()
    assert catalogo.nivel1.activo is False


def test_valor_de_catalogo_en_uso_no_se_desactiva(cliente_admin, catalogo, crear_servicio):
    """P05/D1: clase, criticidad y tipo usados por un servicio activo no se desactivan; uno sin
    uso sí."""
    servicio = crear_servicio(
        "T.01.01", clase=catalogo.clase, criticidad=catalogo.criticidad, tipo=catalogo.tipo
    )
    for entidad, valor in [
        ("claseservicio", catalogo.clase),
        ("criticidad", catalogo.criticidad),
        ("tiposervicio", catalogo.tipo),
    ]:
        assert _bloqueo(cliente_admin.post(_url(entidad, "desactivar", valor.pk))) == [servicio]
        valor.refresh_from_db()
        assert valor.activo, entidad

    servicio.clase = None
    servicio.save()
    assert (
        cliente_admin.post(_url("claseservicio", "desactivar", catalogo.clase.pk)).status_code
        == 302
    )
    catalogo.clase.refresh_from_db()
    assert catalogo.clase.activo is False


def test_usuario_responsable_de_servicios_activos_no_se_desactiva(
    cliente_admin, puesto, crear_usuario, crear_servicio
):
    """P05/D1+D9: un usuario responsable de un servicio activo no se desactiva (el mensaje
    lista los servicios); su detalle los muestra. Al quitarle la asignación (o dar de baja el
    servicio) sí se desactiva."""
    usuario = crear_usuario("responsable")
    servicio = crear_servicio(
        "T.01.01", seccion_responsable=puesto.seccion, usuario_responsable=usuario
    )
    url = reverse("cuentas:usuario_desactivar", args=[usuario.pk])

    respuesta = cliente_admin.post(url, follow=True)
    mensajes = " ".join(str(m) for m in respuesta.context["messages"])
    assert "No se puede desactivar a «responsable»" in mensajes and "T.01.01" in mensajes
    usuario.refresh_from_db()
    assert usuario.is_active
    detalle = cliente_admin.get(reverse("cuentas:usuario_detalle", args=[usuario.pk]))
    assert servicio.get_absolute_url() in detalle.content.decode()

    cliente_admin.post(_url("servicionivel2", "desactivar", servicio.pk))
    assert cliente_admin.post(url).status_code == 302
    usuario.refresh_from_db()
    assert usuario.is_active is False


def test_reactivar_servicio_con_referencias_inactivas_se_rechaza(
    cliente_admin, catalogo, puesto, crear_usuario, crear_servicio
):
    """P05/D1: no se reactiva un N2 bajo un N1 dado de baja ni con un usuario responsable
    inactivo; con todo activo, sí."""
    usuario = crear_usuario("persona")
    servicio = crear_servicio(
        "T.01.01",
        activo=False,
        seccion_responsable=puesto.seccion,
        usuario_responsable=usuario,
    )
    ServicioNivel1.objects.filter(pk=catalogo.nivel1.pk).update(activo=False)
    url = _url("servicionivel2", "reactivar", servicio.pk)

    respuesta = cliente_admin.post(url, follow=True)
    mensajes = " ".join(str(m) for m in respuesta.context["messages"])
    assert "está inactivo" in mensajes
    servicio.refresh_from_db()
    assert servicio.activo is False

    ServicioNivel1.objects.filter(pk=catalogo.nivel1.pk).update(activo=True)
    type(usuario).objects.filter(pk=usuario.pk).update(is_active=False)
    respuesta = cliente_admin.post(url, follow=True)
    mensajes = " ".join(str(m) for m in respuesta.context["messages"])
    assert "«persona» está inactivo" in mensajes
    servicio.refresh_from_db()
    assert servicio.activo is False

    type(usuario).objects.filter(pk=usuario.pk).update(is_active=True)
    assert cliente_admin.post(url).status_code == 302
    servicio.refresh_from_db()
    assert servicio.activo is True


def test_sin_borrado_fisico_ni_cambio_de_estado_por_get(cliente_admin, catalogo, crear_servicio):
    """P05/D1: DELETE no está disponible y GET a desactivar responde 405 sin cambiar nada."""
    servicio = crear_servicio("T.01.01")
    assert cliente_admin.delete(servicio.get_absolute_url()).status_code == 405
    assert cliente_admin.get(_url("servicionivel2", "desactivar", servicio.pk)).status_code == 405
    servicio.refresh_from_db()
    assert servicio.activo
