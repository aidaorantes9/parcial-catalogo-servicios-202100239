"""Contenido inicial del mapeo de correcciones (modelo-datos.md §3.2, D7).

Una sola regla activa: `Demostration` → `Demonstration` en la lista de tipos (H113). Los nombres de
servicios y los códigos SE.12.n no se corrigen (D5, D7).
"""

from django.db import migrations

REGLAS = [
    {
        "ambito": "ETIQUETA_TIPO",
        "valor_original": "Demostration",
        "valor_corregido": "Demonstration",
        "celda_origen": "H113",
        "motivo": "Error de escritura en la lista de tipos",
    },
]


def crear_reglas(apps, schema_editor):
    MapeoCorreccion = apps.get_model("importacion", "MapeoCorreccion")
    for regla in REGLAS:
        MapeoCorreccion.objects.update_or_create(
            ambito=regla["ambito"],
            valor_original=regla["valor_original"],
            defaults={k: v for k, v in regla.items() if k not in ("ambito", "valor_original")},
        )


def quitar_reglas(apps, schema_editor):
    MapeoCorreccion = apps.get_model("importacion", "MapeoCorreccion")
    for regla in REGLAS:
        MapeoCorreccion.objects.filter(
            ambito=regla["ambito"], valor_original=regla["valor_original"]
        ).delete()


class Migration(migrations.Migration):
    dependencies = [("importacion", "0001_initial")]

    operations = [migrations.RunPython(crear_reglas, quitar_reglas)]
