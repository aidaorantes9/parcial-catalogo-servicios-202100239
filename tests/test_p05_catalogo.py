"""P05 (catálogo): código duplicado y referencia inexistente o inactiva.

Rechazo con mensaje comprensible, validado en el servidor (también ante peticiones directas).
"""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from catalogo.models import ClaseServicio, ServicioNivel1, ServicioNivel2, TipoServicio

pytestmark = [pytest.mark.p05, pytest.mark.django_db]

CREAR_N2 = "catalogo:servicionivel2_crear"


def _errores(respuesta, campo):
    assert respuesta.status_code == 200
    return " ".join(respuesta.context["form"].errors.get(campo, []))


def test_codigo_n2_duplicado_se_rechaza_al_crear_y_editar(
    cliente_admin, crear_servicio, datos_servicio
):
    """P05: un servicio de nivel 2 con código repetido se rechaza, también al editar otro."""
    crear_servicio("T.01.01")
    respuesta = cliente_admin.post(reverse(CREAR_N2), datos_servicio("T.01.01"))
    assert "«T.01.01» ya está en uso" in _errores(respuesta, "codigo")
    assert ServicioNivel2.objects.filter(codigo="T.01.01").count() == 1

    otro = crear_servicio("T.01.02")
    respuesta = cliente_admin.post(
        reverse("catalogo:servicionivel2_editar", args=[otro.pk]), datos_servicio("T.01.01")
    )
    assert "ya está en uso" in _errores(respuesta, "codigo")
    otro.refresh_from_db()
    assert otro.codigo == "T.01.02"


def test_codigo_n1_duplicado_se_rechaza(cliente_admin, catalogo):
    """P05: un servicio de nivel 1 con código repetido se rechaza con mensaje."""
    datos = {"codigo": "T.01", "nombre": "Repetido", "estado_revision": "SIN_OBSERVACIONES"}
    respuesta = cliente_admin.post(reverse("catalogo:servicionivel1_crear"), datos)
    assert "«T.01» ya está en uso" in _errores(respuesta, "codigo")
    assert ServicioNivel1.objects.filter(codigo="T.01").count() == 1


def test_valor_de_catalogo_duplicado_o_con_codigo_invalido_se_rechaza(cliente_admin, catalogo):
    """P05: en clase, criticidad y tipo se rechaza el código repetido, la etiqueta repetida y un
    código con formato inválido."""
    url = reverse("catalogo:claseservicio_crear")
    respuesta = cliente_admin.post(url, {"codigo": "CLASE_A", "etiqueta": "Otra", "orden": 1})
    assert "ya está en uso" in _errores(respuesta, "codigo")
    respuesta = cliente_admin.post(url, {"codigo": "CLASE_B", "etiqueta": "Clase A", "orden": 1})
    assert "ya existe" in _errores(respuesta, "etiqueta")
    respuesta = cliente_admin.post(url, {"codigo": "clase b", "etiqueta": "Nueva", "orden": 1})
    assert "mayúsculas" in _errores(respuesta, "codigo")
    assert ClaseServicio.objects.count() == 1

    respuesta = cliente_admin.post(url, {"codigo": "CLASE_B", "etiqueta": "Clase B", "orden": 1})
    assert respuesta.status_code == 302
    nuevo = ClaseServicio.objects.get(codigo="CLASE_B")
    assert nuevo.etiqueta_original == nuevo.etiqueta_mostrada == "Clase B"
    assert nuevo.fila_origen is None


def test_referencia_inexistente_se_rechaza(cliente_admin, datos_servicio):
    """P05: nivel 1, clase, criticidad, tipo, sección o usuario con id inexistente se rechazan
    con mensaje; no se crea el servicio."""
    campos = [
        "nivel1",
        "clase",
        "criticidad",
        "tipo",
        "seccion_responsable",
        "usuario_responsable",
    ]
    for campo in campos:
        respuesta = cliente_admin.post(reverse(CREAR_N2), datos_servicio(**{campo: 999999}))
        assert "no existe" in _errores(respuesta, campo), campo
    assert not ServicioNivel2.objects.exists()


def test_referencia_inactiva_se_rechaza(
    cliente_admin, catalogo, puesto, crear_usuario, crear_valor, datos_servicio
):
    """P05: no se asocia un servicio a un nivel 1, valor de catálogo, sección o usuario
    inactivos; el mensaje indica que está inactivo."""
    n1 = ServicioNivel1.objects.create(codigo="T.09", nombre="Dado de baja", activo=False)
    tipo = crear_valor(TipoServicio, "VIEJO", "Viejo", activo=False)
    seccion = puesto.seccion
    seccion_inactiva = seccion.departamento.secciones.create(
        codigo="SC9", nombre="Inactiva", activo=False
    )
    inactivo = crear_usuario("inactivo", is_active=False)
    casos = [
        ({"nivel1": n1.pk}, "nivel1"),
        ({"tipo": tipo.pk}, "tipo"),
        ({"seccion_responsable": seccion_inactiva.pk}, "seccion_responsable"),
        (
            {"seccion_responsable": seccion.pk, "usuario_responsable": inactivo.pk},
            "usuario_responsable",
        ),
    ]
    for extra, campo in casos:
        respuesta = cliente_admin.post(reverse(CREAR_N2), datos_servicio(**extra))
        assert "inactiv" in _errores(respuesta, campo), campo
    assert not ServicioNivel2.objects.exists()

    # Las opciones de los selects solo incluyen registros activos.
    formulario = cliente_admin.get(reverse(CREAR_N2)).context["form"]
    assert n1 not in formulario.fields["nivel1"].queryset
    assert tipo not in formulario.fields["tipo"].queryset
    assert seccion_inactiva not in formulario.fields["seccion_responsable"].queryset
    assert inactivo not in formulario.fields["usuario_responsable"].queryset


def test_obligatorios_se_validan_en_el_servidor(cliente_admin, datos_servicio):
    """P05: sin nivel 1, código o nombre (o con solo espacios) se rechaza."""
    for campo in ["nivel1", "codigo", "nombre"]:
        valor = "" if campo == "nivel1" else "   "
        respuesta = cliente_admin.post(reverse(CREAR_N2), datos_servicio(**{campo: valor}))
        assert "obligatorio" in _errores(respuesta, campo), campo
    assert not ServicioNivel2.objects.exists()


def test_modelo_rechaza_nivel1_inactivo_fuera_del_formulario(catalogo):
    """P05: la validación del modelo (usada por formularios, importador y comando demo) rechaza
    un nivel 1 inactivo."""
    n1 = ServicioNivel1.objects.create(codigo="T.09", nombre="Dado de baja", activo=False)
    servicio = ServicioNivel2(codigo="T.09.01", nombre="X", nivel1=n1)
    with pytest.raises(ValidationError) as error:
        servicio.full_clean()
    assert "nivel1" in error.value.message_dict


def test_editar_conserva_referencia_que_se_volvio_inactiva(
    cliente_admin, catalogo, crear_servicio, datos_servicio
):
    """P05: un servicio cuyo tipo se dio de baja después puede editarse sin cambiar el tipo (no
    es una asociación nueva), pero no puede cambiar a otro tipo inactivo."""
    servicio = crear_servicio("T.01.01", tipo=catalogo.tipo)
    otro_inactivo = TipoServicio.objects.create(
        codigo="OTRO", etiqueta_original="Otro", etiqueta_mostrada="Otro", orden=1, activo=False
    )
    TipoServicio.objects.filter(pk=catalogo.tipo.pk).update(activo=False)

    datos = datos_servicio("T.01.01", nombre="Nuevo nombre", tipo=catalogo.tipo.pk)
    respuesta = cliente_admin.post(
        reverse("catalogo:servicionivel2_editar", args=[servicio.pk]), datos
    )
    assert respuesta.status_code == 302
    servicio.refresh_from_db()
    assert servicio.nombre == "Nuevo nombre" and servicio.tipo == catalogo.tipo

    datos["tipo"] = otro_inactivo.pk
    respuesta = cliente_admin.post(
        reverse("catalogo:servicionivel2_editar", args=[servicio.pk]), datos
    )
    assert "inactivo" in _errores(respuesta, "tipo")
