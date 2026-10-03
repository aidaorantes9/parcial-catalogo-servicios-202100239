"""Crea (si no existen) la jerarquía DEMO mínima y las cuentas de demostración ADMIN y CONSULTA.

Las credenciales se leen solo del entorno (.env local, nunca versionado). Idempotente: si una cuenta
ya existe, no se duplica ni se cambia su contraseña, salvo con --restablecer.
"""

import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cuentas.models import Rol, Usuario
from organizacion.models import Area, Departamento, Empresa, Puesto, Seccion

CODIGO_DEMO = "DEMO"

# (modelo, campo padre, nombre). Todos llevan es_demo=True: son datos nuevos, no del Excel.
JERARQUIA_DEMO = [
    (Empresa, None, "Empresa de demostración"),
    (Area, "empresa", "Área de demostración"),
    (Departamento, "area", "Departamento de demostración"),
    (Seccion, "departamento", "Sección de demostración"),
    (Puesto, "seccion", "Puesto de demostración"),
]

CUENTAS = [
    (Rol.ADMIN, "DEMO_ADMIN", "Administrador Demo"),
    (Rol.CONSULTA, "DEMO_CONSULTA", "Consulta Demo"),
]
SUFIJOS_OBLIGATORIOS = ["USUARIO", "CORREO", "PASSWORD"]


class Command(BaseCommand):
    help = (
        "Crea la jerarquía DEMO y las cuentas de demostración (ADMIN y CONSULTA) a partir de "
        "DEMO_ADMIN_* y DEMO_CONSULTA_*. Repetirlo no duplica nada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--restablecer",
            action="store_true",
            help="Si las cuentas ya existen, restablece su contraseña, rol y estado activo "
            "con los valores del entorno.",
        )

    def handle(self, *args, restablecer=False, **options):
        datos = self._leer_entorno()
        with transaction.atomic():
            puesto = self._jerarquia_demo()
            for rol, prefijo, _ in CUENTAS:
                self._cuenta(rol, datos[prefijo], puesto, restablecer)

    def _leer_entorno(self):
        faltantes = [
            f"{prefijo}_{sufijo}"
            for _, prefijo, _ in CUENTAS
            for sufijo in SUFIJOS_OBLIGATORIOS
            if not os.environ.get(f"{prefijo}_{sufijo}", "").strip()
        ]
        if faltantes:
            raise CommandError(
                "Faltan variables de entorno: " + ", ".join(faltantes) + ". Defínalas en .env "
                "(ver .env.example) y reinicie el contenedor web (docker compose up -d)."
            )
        datos = {}
        for _, prefijo, nombre_defecto in CUENTAS:
            datos[prefijo] = {
                "username": os.environ[f"{prefijo}_USUARIO"].strip(),
                "email": os.environ[f"{prefijo}_CORREO"].strip(),
                # La contraseña no se recorta: se usa exactamente como está definida.
                "password": os.environ[f"{prefijo}_PASSWORD"],
                "nombre": os.environ.get(f"{prefijo}_NOMBRE", "").strip() or nombre_defecto,
            }
        return datos

    def _jerarquia_demo(self):
        padre = None
        for modelo, campo_padre, nombre in JERARQUIA_DEMO:
            filtro = {"codigo": CODIGO_DEMO}
            if campo_padre:
                filtro[campo_padre] = padre
            registro = modelo.objects.filter(**filtro).first()
            if registro is None:
                registro = modelo(**filtro, nombre=nombre, es_demo=True)
                self._guardar(registro)
                self.stdout.write(f"Creado {modelo._meta.verbose_name}: {registro}")
            padre = registro
        if not padre.activo:
            raise CommandError(
                f"El puesto de demostración «{padre}» existe pero está inactivo; reactívelo "
                "(y a sus superiores) antes de crear las cuentas."
            )
        return padre

    def _cuenta(self, rol, datos, puesto, restablecer):
        usuario = Usuario.objects.filter(username__iexact=datos["username"]).first()
        if usuario is None:
            if Usuario.objects.filter(email__iexact=datos["email"]).exists():
                raise CommandError(
                    f"El correo {datos['email']} ya pertenece a otro usuario; "
                    f"no se puede crear la cuenta {datos['username']}."
                )
            usuario = Usuario(
                username=datos["username"],
                email=Usuario.objects.normalize_email(datos["email"]),
                nombre=datos["nombre"],
                rol=rol,
                puesto=puesto,
            )
            self._asignar_password(usuario, datos["password"])
            self._guardar(usuario)
            self.stdout.write(self.style.SUCCESS(f"Creada cuenta {rol}: {usuario.username}"))
        elif restablecer:
            self._asignar_password(usuario, datos["password"])
            usuario.rol = rol
            usuario.is_active = True
            self._guardar(usuario)
            self.stdout.write(self.style.WARNING(f"Restablecida cuenta {rol}: {usuario.username}"))
        else:
            self.stdout.write(
                f"Ya existe la cuenta {usuario.username}; sin cambios "
                "(use --restablecer para restablecer su contraseña)."
            )

    def _asignar_password(self, usuario, password):
        try:
            validate_password(password, usuario)
        except ValidationError as error:
            raise CommandError(
                f"La contraseña definida para {usuario.username} no cumple los validadores: "
                + " ".join(error.messages)
            ) from error
        usuario.set_password(password)

    def _guardar(self, registro):
        try:
            registro.full_clean()
        except ValidationError as error:
            raise CommandError(f"{registro}: " + " ".join(error.messages)) from error
        registro.save()
