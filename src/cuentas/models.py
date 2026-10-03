from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
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

    La autorización depende solo de `rol`. El campo `puesto` se agrega en la fase de organización.
    """

    # unique=True lo exige Django para USERNAME_FIELD; la restricción sobre lower() evita duplicados
    # que solo difieren en mayúsculas.
    username = models.CharField("usuario", max_length=150, unique=True)
    email = models.EmailField("correo", max_length=254)
    nombre = models.CharField("nombre", max_length=200)
    rol = models.CharField("rol", max_length=10, choices=Rol.choices, default=Rol.CONSULTA)
    is_active = models.BooleanField("activo", default=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email", "nombre"]

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

    @property
    def es_admin(self):
        return self.rol == Rol.ADMIN
