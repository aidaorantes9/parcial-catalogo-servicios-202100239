import pytest
from django.db import connection


@pytest.mark.humo
@pytest.mark.django_db
def test_inicio_responde(client):
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert "Catálogo de Servicios" in respuesta.content.decode()


@pytest.mark.humo
@pytest.mark.django_db
def test_salud_responde_200(client):
    respuesta = client.get("/salud/")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok"}


@pytest.mark.humo
@pytest.mark.django_db
def test_pruebas_usan_base_de_pruebas():
    assert connection.settings_dict["NAME"].startswith("test_")
