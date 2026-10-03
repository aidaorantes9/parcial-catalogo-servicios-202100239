"""Carga datos de demostración: secciones, puestos y usuarios DEMO y asignaciones de responsables.

Requisito del enunciado (§3.3): al menos tres asignaciones válidas. Requiere el catálogo importado.
Todo es dato nuevo de demostración (unidades con `es_demo=True`, usuarios en puestos DEMO); nada se
presenta como proveniente del Excel. Idempotente: repetirlo no duplica nada y nunca sobrescribe una
asignación existente hecha por un administrador. Las asignaciones pasan por
`catalogo.servicios.asignar_responsables` (mismas validaciones que el formulario, D9).

Contraseña de los usuarios demo: `DEMO_RESPONSABLE_PASSWORD` del entorno si está definida; si no,
una contraseña inutilizable (no pueden iniciar sesión hasta que un administrador la cambie).
"""

import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalogo.models import ServicioNivel2
from catalogo.servicios import asignar_responsables
from cuentas.models import Rol, Usuario
from importacion.models import Ejecucion, EstadoEjecucion
from organizacion.demo import asegurar_jerarquia_demo
from organizacion.models import Puesto, Seccion

# (código, nombre) de las secciones DEMO, hijas del departamento DEMO.
SECCIONES = [
    ("DEMO-INF", "Infraestructura (demostración)"),
    ("DEMO-APL", "Aplicaciones (demostración)"),
]
CODIGO_PUESTO = "RESP"
NOMBRE_PUESTO = "Responsable de servicios (demostración)"
# (usuario, nombre, sección).
USUARIOS = [
    ("demo.infraestructura", "Responsable de infraestructura (demo)", "DEMO-INF"),
    ("demo.aplicaciones", "Responsable de aplicaciones (demo)", "DEMO-APL"),
]
# (código original del servicio importado, sección, usuario responsable o None).
ASIGNACIONES = [
    ("SE.01.01", "DEMO-INF", "demo.infraestructura"),
    ("SE.02.02", "DEMO-INF", None),
    ("SE.06.01", "DEMO-APL", "demo.aplicaciones"),
    ("SE.08.01", "DEMO-APL", None),
]
MINIMO_ASIGNACIONES = 3
VARIABLE_PASSWORD = "DEMO_RESPONSABLE_PASSWORD"


class Command(BaseCommand):
    help = (
        "Crea secciones, puestos y usuarios DEMO y al menos tres asignaciones válidas de "
        "responsables sobre servicios importados. Requiere haber importado el catálogo."
    )

    def handle(self, *args, **options):
        self._verificar_catalogo()
        with transaction.atomic():
            puesto_demo = asegurar_jerarquia_demo(self._guardar, self.stdout.write)
            departamento = puesto_demo.seccion.departamento
            secciones = {
                codigo: self._seccion(departamento, codigo, nombre) for codigo, nombre in SECCIONES
            }
            usuarios = {
                username: self._usuario(username, nombre, secciones[seccion])
                for username, nombre, seccion in USUARIOS
            }
            for codigo, seccion, usuario in ASIGNACIONES:
                self._asignar(codigo, secciones[seccion], usuarios.get(usuario))
            self._comprobar()

    # ------------------------------------------------------------------ pasos

    def _verificar_catalogo(self):
        importado = (
            Ejecucion.objects.filter(estado=EstadoEjecucion.EXITOSA).exists()
            and ServicioNivel2.objects.filter(origen__isnull=False).exists()
        )
        if not importado:
            raise CommandError(
                "El catálogo no está importado. Ejecute primero: "
                "python manage.py importar_catalogo (o bash scripts/importar.sh)."
            )

    def _seccion(self, departamento, codigo, nombre):
        seccion = Seccion.objects.filter(departamento=departamento, codigo=codigo).first()
        if seccion is None:
            seccion = Seccion(departamento=departamento, codigo=codigo, nombre=nombre, es_demo=True)
            self._guardar(seccion)
            self.stdout.write(f"Creada sección: {seccion.ruta}")
        puesto = Puesto.objects.filter(seccion=seccion, codigo=CODIGO_PUESTO).first()
        if puesto is None:
            puesto = Puesto(
                seccion=seccion, codigo=CODIGO_PUESTO, nombre=NOMBRE_PUESTO, es_demo=True
            )
            self._guardar(puesto)
            self.stdout.write(f"Creado puesto: {puesto.ruta}")
        return seccion

    def _usuario(self, username, nombre, seccion):
        usuario = Usuario.objects.filter(username__iexact=username).first()
        if usuario is not None:
            self.stdout.write(f"Ya existe el usuario {username}; sin cambios.")
            return usuario
        usuario = Usuario(
            username=username,
            email=f"{username}@example.com",
            nombre=nombre,
            rol=Rol.CONSULTA,
            puesto=Puesto.objects.get(seccion=seccion, codigo=CODIGO_PUESTO),
        )
        password = os.environ.get(VARIABLE_PASSWORD, "")
        if password:
            try:
                validate_password(password, usuario)
            except ValidationError as error:
                raise CommandError(
                    f"{VARIABLE_PASSWORD} no cumple los validadores: " + " ".join(error.messages)
                ) from error
            usuario.set_password(password)
            origen = f"contraseña de {VARIABLE_PASSWORD}"
        else:
            usuario.set_unusable_password()
            origen = f"contraseña inutilizable ({VARIABLE_PASSWORD} no definida)"
        self._guardar(usuario)
        self.stdout.write(self.style.SUCCESS(f"Creado usuario CONSULTA {username} ({origen})."))
        return usuario

    def _asignar(self, codigo, seccion, usuario):
        servicio = ServicioNivel2.objects.filter(codigo_original=codigo).first()
        if servicio is None:
            self.stdout.write(self.style.WARNING(f"{codigo}: no existe; se omite."))
            return
        if not servicio.activo:
            self.stdout.write(self.style.WARNING(f"{codigo}: está dado de baja; se omite."))
            return
        if usuario is not None and usuario.puesto.seccion_id != seccion.pk:
            self.stdout.write(
                self.style.WARNING(
                    f"{codigo}: el usuario {usuario.username} ya no pertenece a {seccion.codigo}; "
                    "se asigna solo la sección."
                )
            )
            usuario = None
        actual = (servicio.seccion_responsable_id, servicio.usuario_responsable_id)
        deseado = (seccion.pk, usuario.pk if usuario else None)
        if actual == deseado:
            self.stdout.write(f"{codigo}: asignación ya existente; sin cambios.")
            return
        if servicio.seccion_responsable_id is not None:
            self.stdout.write(
                self.style.WARNING(
                    f"{codigo}: ya tiene otra asignación ({servicio.seccion_responsable}); se "
                    "conserva."
                )
            )
            return
        try:
            asignar_responsables(servicio, seccion, usuario)
        except ValidationError as error:
            raise CommandError(f"{codigo}: " + " ".join(error.messages)) from error
        quien = f", usuario {usuario.username}" if usuario else ""
        self.stdout.write(self.style.SUCCESS(f"{codigo}: asignado a {seccion.codigo}{quien}."))

    def _comprobar(self):
        """Cuenta las asignaciones DEMO válidas (D9) y exige el mínimo del enunciado."""
        validas = [
            s
            for s in ServicioNivel2.objects.filter(
                activo=True, seccion_responsable__es_demo=True, seccion_responsable__activo=True
            ).select_related("seccion_responsable", "usuario_responsable__puesto")
            if s.usuario_responsable is None
            or s.usuario_responsable.puesto.seccion_id == s.seccion_responsable_id
        ]
        self.stdout.write("")
        self.stdout.write("== Asignaciones de demostración válidas ==")
        for s in validas:
            usuario = s.usuario_responsable.username if s.usuario_responsable else "sin usuario"
            self.stdout.write(f"  {s.codigo:<10} {s.seccion_responsable.codigo:<10} {usuario}")
        secciones = {s.seccion_responsable_id for s in validas}
        con_usuario = [s for s in validas if s.usuario_responsable_id]
        self.stdout.write(
            f"Total: {len(validas)} asignaciones, {len(secciones)} secciones, "
            f"{len(con_usuario)} con usuario responsable."
        )
        if len(validas) < MINIMO_ASIGNACIONES or len(secciones) < 2 or not con_usuario:
            raise CommandError(
                f"Se requieren al menos {MINIMO_ASIGNACIONES} asignaciones válidas en dos "
                "secciones y una con usuario responsable."
            )

    def _guardar(self, registro):
        try:
            registro.full_clean()
        except ValidationError as error:
            raise CommandError(f"{registro}: " + " ".join(error.messages)) from error
        registro.save()
