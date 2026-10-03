"""Agrega Usuario.puesto (supuesto S4) en dos pasos.

Este archivo agrega la columna como NULL y asigna un puesto a los usuarios que ya existan; la migración
0003 la vuelve NOT NULL. Se separan porque PostgreSQL no permite ALTER TABLE en la misma transacción
que tiene eventos de FK diferidos pendientes.

- Base vacía (caso normal): no hay usuarios y no se crea nada.
- Base con usuarios previos (p. ej. pruebas manuales): se crea una jerarquía de transición con código
  MIGRACION en todos sus niveles, **inactiva** de punta a punta, y los usuarios se asignan a su puesto.
  Ningún usuario se borra ni cambia de rol, estado o contraseña, y pueden seguir iniciando sesión.
  Como el puesto está inactivo, al editar uno de esos usuarios el administrador debe elegir un puesto
  activo real (no se pueden crear asociaciones nuevas con él). Es un dato técnico de la migración,
  no proviene del Excel.
"""

import django.db.models.deletion
from django.db import migrations, models

CODIGO = "MIGRACION"
NOMBRE = "Pendiente de asignación (migración cuentas 0002)"


def asignar_puesto_transitorio(apps, schema_editor):
    Usuario = apps.get_model("cuentas", "Usuario")
    sin_puesto = Usuario.objects.filter(puesto__isnull=True)
    if not sin_puesto.exists():
        return
    comunes = {"nombre": NOMBRE, "activo": False}
    empresa, _ = apps.get_model("organizacion", "Empresa").objects.get_or_create(
        codigo=CODIGO, defaults=comunes
    )
    area, _ = apps.get_model("organizacion", "Area").objects.get_or_create(
        empresa=empresa, codigo=CODIGO, defaults=comunes
    )
    departamento, _ = apps.get_model("organizacion", "Departamento").objects.get_or_create(
        area=area, codigo=CODIGO, defaults=comunes
    )
    seccion, _ = apps.get_model("organizacion", "Seccion").objects.get_or_create(
        departamento=departamento, codigo=CODIGO, defaults=comunes
    )
    puesto, _ = apps.get_model("organizacion", "Puesto").objects.get_or_create(
        seccion=seccion, codigo=CODIGO, defaults=comunes
    )
    total = sin_puesto.update(puesto=puesto)
    print(f"\n  cuentas.0002: {total} usuario(s) existente(s) asignado(s) al puesto inactivo "
          f"{CODIGO}; reasígnelos a un puesto activo desde Usuarios > Editar.")


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0001_initial"),
        ("organizacion", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="puesto",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="usuarios",
                to="organizacion.puesto",
                verbose_name="puesto",
            ),
        ),
        migrations.RunPython(asignar_puesto_transitorio, migrations.RunPython.noop),
    ]
