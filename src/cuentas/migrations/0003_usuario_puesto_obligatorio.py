"""Vuelve obligatorio Usuario.puesto (ver la explicación en 0002_usuario_puesto)."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0002_usuario_puesto"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usuario",
            name="puesto",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="usuarios",
                to="organizacion.puesto",
                verbose_name="puesto",
            ),
        ),
    ]
