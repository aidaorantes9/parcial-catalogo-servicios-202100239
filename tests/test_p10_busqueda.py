"""P10: buscar y filtrar servicios de nivel 2.

Con datos controlados creados en la prueba, la búsqueda por código y por nombre y cada filtro
(por separado y combinados) devuelven exactamente los registros esperados; la paginación conserva
los filtros.
"""

from types import SimpleNamespace

import pytest
from django.urls import reverse

from catalogo.models import ClaseServicio, Criticidad, ServicioNivel1, TipoServicio

pytestmark = [pytest.mark.p10, pytest.mark.django_db]

LISTA = reverse("catalogo:servicionivel2_lista")


@pytest.fixture
def datos(catalogo, puesto, crear_valor, crear_servicio):
    """Cinco servicios con combinaciones conocidas de atributos (S5 está dado de baja)."""
    n1_a = catalogo.nivel1
    n1_b = ServicioNivel1.objects.create(codigo="T.02", nombre="Otro nivel 1")
    c1, k1, t1 = catalogo.clase, catalogo.criticidad, catalogo.tipo
    c2 = crear_valor(ClaseServicio, "CLASE_B", "Clase B", 1)
    k2 = crear_valor(Criticidad, "ALTA", "Alta", 1)
    t2 = crear_valor(TipoServicio, "TIPO_B", "Tipo B", 1)
    s1 = puesto.seccion
    s2 = s1.departamento.secciones.create(codigo="SC2", nombre="Sección 2")
    comun = {"clase": c1, "criticidad": k1, "tipo": t1}
    crear_servicio(
        "T.01.01", nombre="Gestionar redes", activo_excel="S", seccion_responsable=s1, **comun
    )
    crear_servicio(
        "T.01.02",
        nombre="Monitorear redes",
        activo_excel="N",
        clase=c2,
        criticidad=k2,
        tipo=t2,
        estado_revision="PENDIENTE_REVISION",
    )
    crear_servicio(
        "T.02.01", nivel1=n1_b, nombre="Respaldar datos", estado_revision="PENDIENTE_REVISION"
    )
    crear_servicio(
        "T.02.02",
        nivel1=n1_b,
        nombre="Gestionar copias",
        activo_excel="Si",
        clase=c1,
        criticidad=k2,
        tipo=t1,
        seccion_responsable=s2,
        estado_revision="REVISADO",
    )
    crear_servicio(
        "T.02.03",
        nivel1=n1_b,
        nombre="Servicio retirado",
        activo_excel="S",
        activo=False,
        seccion_responsable=s1,
        **comun,
    )
    return SimpleNamespace(
        n1_a=n1_a, n1_b=n1_b, c1=c1, c2=c2, k1=k1, k2=k2, t1=t1, t2=t2, s1=s1, s2=s2
    )


def _codigos(cliente, **parametros):
    respuesta = cliente.get(LISTA, parametros)
    assert respuesta.status_code == 200
    return [s.codigo for s in respuesta.context["registros"]]


ACTIVOS = ["T.01.01", "T.01.02", "T.02.01", "T.02.02"]


def test_sin_filtros_muestra_solo_registros_activos(cliente_consulta, datos):
    """P10: por defecto el listado muestra los registros activos (estado del registro)."""
    assert _codigos(cliente_consulta) == ACTIVOS


def test_busqueda_por_codigo_y_por_nombre(cliente_consulta, datos):
    """P10: la búsqueda encuentra por código parcial y por nombre sin distinguir mayúsculas."""
    assert _codigos(cliente_consulta, q="T.02") == ["T.02.01", "T.02.02"]
    assert _codigos(cliente_consulta, q="t.01.02") == ["T.01.02"]
    assert _codigos(cliente_consulta, q="GESTIONAR") == ["T.01.01", "T.02.02"]
    assert _codigos(cliente_consulta, q="redes") == ["T.01.01", "T.01.02"]
    assert _codigos(cliente_consulta, q="no existe") == []


def test_cada_filtro_por_separado(cliente_consulta, datos):
    """P10: cada filtro aislado devuelve exactamente los registros esperados, incluido
    «Sin dato» para los campos sin valor."""
    d = datos
    casos = [
        ({"nivel1": d.n1_a.pk}, ["T.01.01", "T.01.02"]),
        ({"nivel1": d.n1_b.pk}, ["T.02.01", "T.02.02"]),
        ({"estado": "inactivos"}, ["T.02.03"]),
        ({"estado": "todos"}, ACTIVOS + ["T.02.03"]),
        ({"activo_excel": "S"}, ["T.01.01"]),
        ({"activo_excel": "N"}, ["T.01.02"]),
        ({"activo_excel": "desconocido"}, ["T.02.01"]),
        ({"activo_excel": "otros"}, ["T.02.02"]),
        ({"activo_excel": ""}, ACTIVOS),
        ({"clase": d.c1.pk}, ["T.01.01", "T.02.02"]),
        ({"clase": d.c2.pk}, ["T.01.02"]),
        ({"clase": "sin"}, ["T.02.01"]),
        ({"criticidad": d.k2.pk}, ["T.01.02", "T.02.02"]),
        ({"criticidad": "sin"}, ["T.02.01"]),
        ({"tipo": d.t1.pk}, ["T.01.01", "T.02.02"]),
        ({"tipo": "sin"}, ["T.02.01"]),
        ({"revision": "PENDIENTE_REVISION"}, ["T.01.02", "T.02.01"]),
        ({"revision": "REVISADO"}, ["T.02.02"]),
        ({"revision": "SIN_OBSERVACIONES"}, ["T.01.01"]),
        ({"seccion": d.s1.pk}, ["T.01.01"]),
        ({"seccion": d.s2.pk}, ["T.02.02"]),
        ({"seccion": "sin"}, ["T.01.02", "T.02.01"]),
    ]
    for parametros, esperados in casos:
        assert _codigos(cliente_consulta, **parametros) == esperados, parametros


def test_filtros_combinados(cliente_consulta, datos):
    """P10: los filtros se combinan entre sí (condición Y) y con la búsqueda."""
    d = datos
    casos = [
        ({"nivel1": d.n1_b.pk, "clase": d.c1.pk}, ["T.02.02"]),
        ({"q": "gestionar", "seccion": d.s2.pk}, ["T.02.02"]),
        (
            {"nivel1": d.n1_a.pk, "activo_excel": "N", "revision": "PENDIENTE_REVISION"},
            ["T.01.02"],
        ),
        ({"estado": "todos", "clase": d.c1.pk, "criticidad": d.k1.pk}, ["T.01.01", "T.02.03"]),
        ({"estado": "todos", "activo_excel": "S", "nivel1": d.n1_b.pk}, ["T.02.03"]),
        ({"clase": "sin", "tipo": "sin", "seccion": "sin"}, ["T.02.01"]),
        ({"q": "redes", "criticidad": d.k1.pk, "tipo": d.t2.pk}, []),
    ]
    for parametros, esperados in casos:
        assert _codigos(cliente_consulta, **parametros) == esperados, parametros


def test_valores_de_filtro_invalidos_se_ignoran(cliente_consulta, datos):
    """P10: un parámetro con valor no válido no provoca error ni filtra."""
    parametros = {"clase": "abc", "activo_excel": "quizas", "revision": "X", "estado": "raro"}
    assert _codigos(cliente_consulta, **parametros) == ACTIVOS


def test_paginacion_conserva_los_filtros(cliente_consulta, datos, crear_servicio):
    """P10: con 25 resultados filtrados, la página 1 tiene 20, el enlace «Siguiente» conserva
    los filtros y la página 2 trae los 5 restantes, todos con los criterios."""
    for i in range(25):
        crear_servicio(f"P.{i:02d}", nombre=f"Paginado {i:02d}", clase=datos.c2, activo_excel="N")
    crear_servicio("P.99", nombre="Paginado sin clase", activo_excel="N")
    parametros = {"q": "Paginado", "clase": datos.c2.pk, "activo_excel": "N"}

    respuesta = cliente_consulta.get(LISTA, parametros)
    pagina = respuesta.context["page_obj"]
    assert pagina.paginator.count == 25 and len(pagina.object_list) == 20
    filtros = respuesta.context["filtros"]
    assert f"clase={datos.c2.pk}" in filtros and "q=Paginado" in filtros
    assert "activo_excel=N" in filtros and "page" not in filtros
    assert f'href="?{filtros.replace("&", "&amp;")}&amp;page=2"' in respuesta.content.decode()

    segunda = cliente_consulta.get(LISTA, {**parametros, "page": 2})
    codigos = [s.codigo for s in segunda.context["registros"]]
    assert codigos == [f"P.{i:02d}" for i in range(20, 25)]
    assert all(s.clase_id == datos.c2.pk for s in segunda.context["registros"])
    # Los selects de la página 2 siguen mostrando los criterios elegidos.
    assert segunda.context["criterios"]["clase"] == str(datos.c2.pk)
