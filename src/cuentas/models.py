from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower


class Rol(models.TextChoices):
    ADMIN = "ADMIN", "Administrador"
    CONSULTA = "CONSULTA", "Consulta"


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, email, nombre, password=None, **extra):
        if not username:
            raise ValueError("El usuario es obligatorio.")
        if not email:
            raise ValueError("El correo es obligatorio.")
        usuario = self.model(
            username=username,
            email=self.normalize_email(email),
            nombre=nombre,
            **extra,
        )
        # Sin contraseña se guarda un hash inutilizable, nunca texto plano.
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, username, email, nombre, password=None, **extra):
        # No existe is_superuser (supuesto S6): el privilegio máximo es el rol ADMIN.
        extra["rol"] = Rol.ADMIN
        return self.create_user(username, email, nombre, password, **extra)

    def get_by_natural_key(self, username):
        return self.get(username__iexact=username)


class Usuario(AbstractBaseUser):
    """Usuario local. Se basa en AbstractBaseUser, sin is_staff ni is_superuser (S6).

    La autorización depende solo de `rol`. El puesto es obligatorio (supuesto S4) y la empresa se
    deriva de la jerarquía del puesto; no se guarda una relación paralela que pueda contradecirla.
    """

    # unique=True lo exige Django para USERNAME_FIELD; la restricción sobre lower() evita duplicados
    # que solo difieren en mayúsculas.
    username = models.CharField("usuario", max_length=150, unique=True)
    email = models.EmailField("correo", max_length=254)
    nombre = models.CharField("nombre", max_length=200)
    rol = models.CharField("rol", max_length=10, choices=Rol.choices, default=Rol.CONSULTA)
    is_active = models.BooleanField("activo", default=True)
    puesto = models.ForeignKey(
        "organizacion.Puesto",
        on_delete=models.PROTECT,
        related_name="usuarios",
        verbose_name="puesto",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email", "nombre", "puesto"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            models.UniqueConstraint(Lower("username"), name="usuario_username_unico_ci"),
            models.UniqueConstraint(Lower("email"), name="usuario_email_unico_ci"),
            models.CheckConstraint(
                condition=models.Q(rol__in=[Rol.ADMIN, Rol.CONSULTA]),
                name="usuario_rol_valido",
            ),
            models.CheckConstraint(
                condition=~models.Q(username__regex=r"^\s*$"),
                name="usuario_username_no_vacio",
            ),
            models.CheckConstraint(
                condition=~models.Q(nombre__regex=r"^\s*$"),
                name="usuario_nombre_no_vacio",
            ),
        ]

    def __str__(self):
        return self.username

    @classmethod
    def from_db(cls, db, field_names, values):
        instancia = super().from_db(db, field_names, values)
        valores = dict(zip(field_names, values, strict=True))
        instancia._puesto_original_id = valores.get("puesto_id")
        instancia._activo_original = valores.get("is_active")
        return instancia

    @property
    def es_admin(self):
        return self.rol == Rol.ADMIN

    @property
    def empresa(self):
        """Empresa derivada de Puesto → Sección → Departamento → Área → Empresa."""
        return self.puesto.seccion.departamento.area.empresa

    def servicios_a_cargo(self, solo_activos=False):
        """Servicios de nivel 2 de los que es usuario responsable."""
        if not self.pk:
            return []
        servicios = self.servicios_asignados.order_by("codigo")
        return list(servicios.filter(activo=True) if solo_activos else servicios)

    def clean(self):
        super().clean()
        self._validar_desactivacion()
        if self.puesto_id is None:
            return
        cambia_puesto = self._state.adding or self.puesto_id != getattr(
            self, "_puesto_original_id", None
        )
        if cambia_puesto and not self.puesto.activo:
            raise ValidationError(
                {"puesto": f"El puesto «{self.puesto}» está inactivo; elija un puesto activo."}
            )
        if cambia_puesto and not self._state.adding:
            self._validar_cambio_de_seccion()

    def _validar_desactivacion(self):
        """D1 + D9: no se desactiva a un usuario responsable de servicios activos (quedarían
        asignados a alguien que ya no puede actuar); se listan los servicios."""
        if (
            self._state.adding
            or self.is_active
            or getattr(self, "_activo_original", None) is not True
        ):
            return
        servicios = self.servicios_a_cargo(solo_activos=True)
        if servicios:
            lista = ", ".join(s.codigo for s in servicios)
            raise ValidationError(
                f"No se puede desactivar a «{self.username}»: es usuario responsable de "
                f"servicios activos ({lista}). Asigne otro responsable o quítelo primero."
            )

    def _validar_cambio_de_seccion(self):
        """D9: el usuario responsable debe pertenecer a la sección responsable; no se le cambia a
        un puesto de otra sección mientras siga asignado a algún servicio (de cualquier estado)."""
        from organizacion.models import Puesto

        seccion_anterior = (
            Puesto.objects.filter(pk=self._puesto_original_id)
            .values_list("seccion_id", flat=True)
            .first()
        )
        if seccion_anterior == self.puesto.seccion_id:
            return
        servicios = self.servicios_a_cargo()
        if servicios:
            lista = ", ".join(s.codigo for s in servicios)
            raise ValidationError(
                {
                    "puesto": f"No se puede cambiar a un puesto de otra sección: «{self.username}» "
                    f"es usuario responsable de servicios de su sección actual ({lista}). "
                    "Asigne otro responsable o quítelo primero."
                }
            )
