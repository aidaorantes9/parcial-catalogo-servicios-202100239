"""Configuración de Django. Todo valor sensible o de entorno se lee de variables de entorno."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _requerida(nombre):
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise ImproperlyConfigured(
            f"Falta la variable de entorno {nombre}. Copie .env.example a .env y defina un valor."
        )
    return valor


def _booleana(nombre, por_defecto=False):
    valor = os.environ.get(nombre)
    if valor is None or not valor.strip():
        return por_defecto
    return valor.strip().lower() in {"1", "true", "si", "sí", "yes", "on"}


def _lista(nombre):
    return [v.strip() for v in os.environ.get(nombre, "").split(",") if v.strip()]


SECRET_KEY = _requerida("SECRET_KEY")
DEBUG = _booleana("DEBUG")
ALLOWED_HOSTS = _lista("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cuentas",
    "organizacion",
    "catalogo",
    "importacion",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Borra la sesión de un usuario desactivado o eliminado en su siguiente petición.
    "cuentas.middleware.CerrarSesionInvalidaMiddleware",
    # Todo requiere sesión salvo las vistas marcadas con @login_not_required (login y /salud/).
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

_nombre_bd = _requerida("POSTGRES_DB")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _nombre_bd,
        "USER": _requerida("POSTGRES_USER"),
        "PASSWORD": _requerida("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        # pytest-django crea y destruye esta base; las pruebas nunca tocan la base de evaluación.
        "TEST": {"NAME": f"test_{_nombre_bd}"},
    }
}

AUTH_USER_MODEL = "cuentas.Usuario"
AUTHENTICATION_BACKENDS = ["cuentas.backends.UsuarioOCorreoBackend"]
LOGIN_URL = "cuentas:entrar"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "cuentas:entrar"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-gt"
TIME_ZONE = "America/Guatemala"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sesiones en base de datos (django_session): el cierre de sesión borra la fila en el servidor.
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# Activar (1) cuando se sirva por HTTPS; en el entorno local de evaluación se usa HTTP.
SESSION_COOKIE_SECURE = _booleana("COOKIES_SEGURAS")
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["consola"], "level": "INFO"},
}
