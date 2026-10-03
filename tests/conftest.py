from types import SimpleNamespace

import pytest

from catalogo.models import ClaseServicio, Criticidad, ServicioNivel1, ServicioNivel2, TipoServicio
from cuentas.models import Rol, Usuario
from organizacion.models import Area, Departamento, Empresa, Puesto, Seccion

# Contraseña solo para la base de pruebas (test_*), que pytest-django crea y destruye.
PASSWORD = "Prueba-Segura-2026!"


@pytest.fixture
def puesto(db):
    empresa = Empresa.objects.create(codigo="EMP", nombre="Empresa de prueba")
    area = Area.objects.create(empresa=empresa, codigo="AR", nombre="Área de prueba")
    departamento = Departamento.objects.create(area=area, codigo="DP", nombre="Depto de prueba")
    seccion = Seccion.objects.create(departamento=departamento, codigo="SC", nombre="Sección")
    return Puesto.objects.create(seccion=seccion, codigo="PU", nombre="Puesto de prueba")


@pytest.fixture
def crear_usuario(puesto):
    def crear(username, rol=Rol.CONSULTA, **extra):
        datos = {
            "email": f"{username}@example.com",
            "nombre": username.title(),
            "rol": rol,
            "puesto": puesto,
        }
        datos.update(extra)
        return Usuario.objects.create_user(username, password=PASSWORD, **datos)

    return crear


@pytest.fixture
def admin(crear_usuario):
    return crear_usuario("admin", rol=Rol.ADMIN, email="Admin@Example.com")


@pytest.fixture
def consulta(crear_usuario):
    return crear_usuario("consulta", rol=Rol.CONSULTA)


@pytest.fixture
def cliente_admin(client, admin):
    client.force_login(admin)
    return client


@pytest.fixture
def cliente_consulta(client, consulta):
    client.force_login(consulta)
    return client


# ---------------------------------------------------------------- catálogo (datos controlados)


def _valor(modelo, codigo, etiqueta, orden=0, **extra):
    return modelo.objects.create(
        codigo=codigo, etiqueta_original=etiqueta, etiqueta_mostrada=etiqueta, orden=orden, **extra
    )


@pytest.fixture
def catalogo(db):
    """Un nivel 1 y un valor de cada catálogo, creados en la prueba (no dependen del Excel)."""
    return SimpleNamespace(
        nivel1=ServicioNivel1.objects.create(codigo="T.01", nombre="Nivel 1 de prueba"),
        clase=_valor(ClaseServicio, "CLASE_A", "Clase A"),
        criticidad=_valor(Criticidad, "MEDIA", "Media"),
        tipo=_valor(TipoServicio, "TIPO_A", "Tipo A"),
    )


@pytest.fixture
def crear_valor(db):
    return _valor


@pytest.fixture
def crear_servicio(catalogo):
    """Crea un servicio de nivel 2 directamente con el ORM (sin validaciones del formulario)."""

    def crear(codigo, **extra):
        datos = {"nivel1": catalogo.nivel1, "nombre": f"Servicio {codigo}"}
        datos.update(extra)
        return ServicioNivel2.objects.create(codigo=codigo, **datos)

    return crear


@pytest.fixture
def datos_servicio(catalogo):
    """Datos POST completos del formulario de nivel 2; los campos opcionales van vacíos."""

    def datos(codigo="T.01.01", **extra):
        valores = {
            "nivel1": catalogo.nivel1.pk,
            "codigo": codigo,
            "nombre": f"Servicio {codigo}",
            "activo_excel": "",
            "clase": "",
            "criticidad": "",
            "tipo": "",
            "descripcion": "",
            "metrica": "",
            "minimo": "",
            "maximo": "",
            "estado_revision": "SIN_OBSERVACIONES",
            "seccion_responsable": "",
            "usuario_responsable": "",
        }
        valores.update(extra)
        return valores

    return datos
