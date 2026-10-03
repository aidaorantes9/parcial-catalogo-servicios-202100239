import pytest

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
        datos = {"email": f"{username}@example.com", "nombre": username.title(), "rol": rol}
        datos.update(extra)
        return Usuario.objects.create_user(username, password=PASSWORD, puesto=puesto, **datos)

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
