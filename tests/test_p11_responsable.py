"""P11: asignar como responsable a un usuario de una sección distinta.

D9: el usuario responsable debe pertenecer a la sección responsable. Se valida con la función de
servicio común (formularios, importador y comando demo) y en `clean()`; además, el CHECK
ck_n2_usuario_requiere_seccion impide un usuario sin sección. No se puede cambiar el puesto de un
responsable a otra sección (ni mover su puesto) mientras siga asignado.
"""

from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from catalogo.models import ServicioNivel2
from catalogo.servicios import asignar_responsables
from cuentas.models import Usuario
from organizacion.models import Puesto

pytestmark = [pytest.mark.p11, pytest.mark.django_db]

CREAR = "catalogo:servicionivel2_crear"


@pytest.fixture
def org(puesto, crear_usuario):
    """Dos secciones del mismo departamento, cada una con un puesto y un usuario."""
    seccion1 = puesto.seccion
    seccion2 = seccion1.departamento.secciones.create(codigo="SC2", nombre="Sección 2")
    puesto2 = Puesto.objects.create(seccion=seccion2, codigo="PU2", nombre="Puesto 2")
    return SimpleNamespace(
        seccion1=seccion1,
        seccion2=seccion2,
        puesto1=puesto,
        puesto2=puesto2,
        u1=crear_usuario("uno"),
        u2=crear_usuario("dos", puesto=puesto2),
    )


def _errores(respuesta, campo):
    assert respuesta.status_code == 200
    return " ".join(respuesta.context["form"].errors.get(campo, []))


def test_usuario_de_otra_seccion_se_rechaza_en_el_formulario(
    cliente_admin, org, datos_servicio, crear_servicio
):
    """P11: sección 1 con un usuario de la sección 2 → rechazo con mensaje y nada se guarda;
    al editar un servicio existente también."""
    datos = datos_servicio(seccion_responsable=org.seccion1.pk, usuario_responsable=org.u2.pk)
    respuesta = cliente_admin.post(reverse(CREAR), datos)
    mensaje = _errores(respuesta, "usuario_responsable")
    assert "«dos» pertenece a la sección «SC2 — Sección 2»" in mensaje
    assert "no a la sección responsable «SC — Sección»" in mensaje
    assert not ServicioNivel2.objects.exists()

    servicio = crear_servicio("T.01.01", seccion_responsable=org.seccion1)
    url = reverse("catalogo:servicionivel2_editar", args=[servicio.pk])
    respuesta = cliente_admin.post(url, datos)
    assert "pertenece a la sección" in _errores(respuesta, "usuario_responsable")
    servicio.refresh_from_db()
    assert servicio.usuario_responsable_id is None


def test_usuario_sin_seccion_se_rechaza(cliente_admin, org, datos_servicio, crear_servicio):
    """P11: usuario responsable sin sección responsable → rechazo en el formulario, en la
    función de servicio y en la base (CHECK)."""
    respuesta = cliente_admin.post(reverse(CREAR), datos_servicio(usuario_responsable=org.u1.pk))
    assert "sin sección responsable" in _errores(respuesta, "usuario_responsable")
    assert not ServicioNivel2.objects.exists()

    servicio = crear_servicio("T.01.01")
    with pytest.raises(ValidationError) as error:
        asignar_responsables(servicio, None, org.u1)
    assert "usuario_responsable" in error.value.message_dict

    with pytest.raises(IntegrityError, match="ck_n2_usuario_requiere_seccion"):
        with transaction.atomic():
            ServicioNivel2.objects.filter(pk=servicio.pk).update(usuario_responsable=org.u1)


def test_funcion_de_servicio_comun_valida_la_seccion(org, crear_servicio):
    """P11: `asignar_responsables` (la que usarán el importador y el comando demo) rechaza un
    usuario de otra sección y acepta uno de la misma."""
    servicio = crear_servicio("T.01.01")
    with pytest.raises(ValidationError) as error:
        asignar_responsables(servicio, org.seccion1, org.u2)
    assert "pertenece a la sección" in " ".join(error.value.message_dict["usuario_responsable"])
    assert ServicioNivel2.objects.get(pk=servicio.pk).usuario_responsable_id is None

    asignar_responsables(servicio, org.seccion1, org.u1)
    servicio.refresh_from_db()
    assert (servicio.seccion_responsable, servicio.usuario_responsable) == (org.seccion1, org.u1)


def test_asignacion_valida_se_guarda_y_se_ve_en_la_ficha(
    client, admin, consulta, org, datos_servicio
):
    """P11 (caso positivo): sección y usuario de esa sección se guardan; la ficha los muestra
    (a CONSULTA sin enlace a la pantalla de usuarios, que es solo de ADMIN)."""
    datos = datos_servicio(seccion_responsable=org.seccion2.pk, usuario_responsable=org.u2.pk)
    client.force_login(admin)
    assert client.post(reverse(CREAR), datos).status_code == 302
    servicio = ServicioNivel2.objects.get()
    assert servicio.usuario_responsable == org.u2
    detalle_usuario = reverse("cuentas:usuario_detalle", args=[org.u2.pk])
    assert detalle_usuario in client.get(servicio.get_absolute_url()).content.decode()

    client.force_login(consulta)
    contenido = client.get(servicio.get_absolute_url()).content.decode()
    assert "dos — Dos" in contenido and "SC2" in contenido
    assert detalle_usuario not in contenido


def test_solo_secciones_y_usuarios_activos(cliente_admin, org, crear_usuario, datos_servicio):
    """P11: no se asigna un usuario inactivo aunque sea de la sección."""
    inactivo = crear_usuario("tres", is_active=False)
    datos = datos_servicio(seccion_responsable=org.seccion1.pk, usuario_responsable=inactivo.pk)
    respuesta = cliente_admin.post(reverse(CREAR), datos)
    assert "inactivo" in _errores(respuesta, "usuario_responsable")
    assert not ServicioNivel2.objects.exists()


def test_cambiar_puesto_de_responsable_a_otra_seccion_se_rechaza(
    cliente_admin, org, crear_servicio
):
    """P11: mover al responsable a un puesto de otra sección → rechazo con los servicios
    afectados; a otro puesto de la misma sección sí se permite; tras quitarle la asignación,
    también a otra sección."""
    servicio = crear_servicio(
        "T.01.01", seccion_responsable=org.seccion1, usuario_responsable=org.u1
    )
    url = reverse("cuentas:usuario_editar", args=[org.u1.pk])
    datos = {"nombre": "Uno", "email": "uno@example.com", "rol": "CONSULTA"}

    respuesta = cliente_admin.post(url, {**datos, "puesto": org.puesto2.pk})
    mensaje = _errores(respuesta, "puesto")
    assert "otra sección" in mensaje and "T.01.01" in mensaje
    org.u1.refresh_from_db()
    assert org.u1.puesto == org.puesto1

    mismo = Puesto.objects.create(seccion=org.seccion1, codigo="PU3", nombre="Puesto 3")
    assert cliente_admin.post(url, {**datos, "puesto": mismo.pk}).status_code == 302
    org.u1.refresh_from_db()
    assert org.u1.puesto == mismo

    asignar_responsables(servicio, org.seccion1, None)
    assert cliente_admin.post(url, {**datos, "puesto": org.puesto2.pk}).status_code == 302
    org.u1.refresh_from_db()
    assert org.u1.puesto == org.puesto2


def test_cambio_de_puesto_se_valida_en_el_modelo(org, crear_servicio):
    """P11: la regla está en `Usuario.clean()`, no solo en el formulario; también cuenta un
    servicio dado de baja que conserva la asignación."""
    crear_servicio(
        "T.01.01", seccion_responsable=org.seccion1, usuario_responsable=org.u1, activo=False
    )
    usuario = Usuario.objects.get(pk=org.u1.pk)
    usuario.puesto = org.puesto2
    with pytest.raises(ValidationError) as error:
        usuario.full_clean()
    assert "puesto" in error.value.message_dict


def test_mover_puesto_de_un_responsable_a_otra_seccion_se_rechaza(
    cliente_admin, org, crear_servicio
):
    """P11: editar el puesto para cambiarlo de sección cambiaría la sección de su usuario
    responsable; se rechaza."""
    crear_servicio("T.01.01", seccion_responsable=org.seccion1, usuario_responsable=org.u1)
    url = reverse("organizacion:puesto_editar", args=[org.puesto1.pk])
    datos = {"seccion": org.seccion2.pk, "codigo": "PU", "nombre": "Puesto de prueba"}
    respuesta = cliente_admin.post(url, datos)
    assert "uno" in _errores(respuesta, "seccion")
    org.puesto1.refresh_from_db()
    assert org.puesto1.seccion == org.seccion1
