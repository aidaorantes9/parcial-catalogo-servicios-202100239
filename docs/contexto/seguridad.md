# Seguridad: autenticación, sesión y autorización

Describe cómo está implementada la seguridad de la aplicación (fase 5). Fuentes: `AGENTS.md` §4.10–4.11 y §8,
`docs/contexto/enunciado.md` §3.1, `docs/contexto/modelo-datos.md` (`cuentas_usuario`, supuestos S4–S6).
Pruebas que lo comprueban: `tests/test_p01_login.py`, `tests/test_p02_sesion.py`, `tests/test_p03_roles.py`,
`tests/test_usuarios_admin.py`, `tests/test_crear_cuentas_demo.py`.

## 1. Contraseñas: Argon2id

| Aspecto | Implementación |
|---|---|
| Algoritmo | `Argon2PasswordHasher` de Django (paquete `argon2-cffi`), primero en `PASSWORD_HASHERS` (`src/config/settings.py`). Formato guardado: `argon2$argon2id$v=19$m=…,t=…,p=…$<sal>$<hash>` |
| Por qué | Argon2id ganó la Password Hashing Competition y es la primera recomendación de OWASP. Es lento y usa mucha memoria a propósito, lo que encarece los ataques por fuerza bruta con GPU/ASIC. Cada hash lleva su propia sal aleatoria, así que dos contraseñas iguales dan hashes distintos. No es reversible (no es cifrado) |
| PBKDF2 | Queda segundo en la lista solo para poder verificar hashes antiguos; Django los vuelve a calcular con Argon2 al iniciar sesión. Hoy no hay ninguno |
| Validación | `AUTH_PASSWORD_VALIDATORS` de Django (similitud con usuario/correo/nombre, longitud mínima 8, contraseñas comunes, solo números). Se aplican al crear usuarios, al cambiar contraseñas y en `crear_cuentas_demo` |
| Exposición | Ningún formulario, plantilla ni listado incluye el campo `password`. La plantilla común `cuentas/_datos_usuario.html` muestra solo datos funcionales. Probado en P03 para CONSULTA y para ADMIN |

## 2. Inicio de sesión

- Backend propio `cuentas.backends.UsuarioOCorreoBackend` (único en `AUTHENTICATION_BACKENDS`): busca por
  `username` **o** `email` sin distinguir mayúsculas (`iexact`), verifica el hash y rechaza `is_active = false`.
  No hay proveedores externos.
- Mensaje de error único para usuario inexistente, contraseña incorrecta o cuenta inactiva
  (`MENSAJE_LOGIN_INVALIDO` en `cuentas/forms.py`): no revela si la cuenta existe.
- Si el identificador no existe, igual se calcula un hash Argon2 para que el tiempo de respuesta no lo delate.
- `LoginView` de Django rota el identificador de sesión al iniciar sesión (`cycle_key`), lo que evita la
  fijación de sesión.

## 3. Sesión y cierre de sesión

| Aspecto | Implementación |
|---|---|
| Almacenamiento | Sesiones en la base de datos (`django_session`, `SESSION_ENGINE = …backends.db`). La cookie solo lleva un identificador aleatorio |
| Cookie | `HttpOnly`, `SameSite=Lax`, caduca a las 8 h y al cerrar el navegador. `Secure` se activa con `COOKIES_SEGURAS=1` cuando se sirva por HTTPS (en local se usa HTTP) |
| Cierre de sesión | `/salir/` usa `LogoutView`, que **solo acepta POST** (un GET con sesión responde 405) y exige token CSRF. Llama a `logout()` → `session.flush()`: borra la fila de `django_session`. La cookie anterior deja de servir aunque alguien la haya copiado (probado en P02 reutilizando la cookie en otro cliente) |
| Cambio de contraseña | Django guarda en la sesión un hash derivado de la contraseña y lo compara en cada petición; al cambiarla, las demás sesiones del usuario quedan inválidas. Si el administrador cambia su propia contraseña se usa `update_session_auth_hash` para no cerrar la suya |

## 4. Usuarios inactivos

1. **No pueden iniciar sesión**: el backend rechaza `is_active = false` y se muestra el mensaje genérico.
2. **Sesión abierta al desactivarlos**: en cada petición, `ModelBackend.get_user` devuelve `None` para un
   usuario inactivo, por lo que `AuthenticationMiddleware` lo trata como anónimo. Además
   `cuentas.middleware.CerrarSesionInvalidaMiddleware` detecta una sesión con usuario que ya no es válido y la
   borra del servidor (`flush`); `LoginRequiredMiddleware` lo redirige al login. Aunque el usuario se reactive
   después, esa cookie no vuelve a servir (probado en P02).
3. Un administrador no puede desactivarse a sí mismo ni quitarse el rol ADMIN (evita quedarse sin
   administradores por error).

## 5. Protección CSRF

- `CsrfViewMiddleware` activo; todos los formularios POST (login, logout, alta, edición, desactivar, reactivar,
  cambio de contraseña) incluyen `{% csrf_token %}`. Un POST sin token responde 403 (probado en P02 con el
  logout).
- Ninguna operación que modifica datos acepta GET: desactivar, reactivar y cerrar sesión responden 405 a GET.
- `CSRF_COOKIE_HTTPONLY = True` y `X_FRAME_OPTIONS = "DENY"` (evita clickjacking).

## 6. Roles y dónde se valida

| Rol | Permisos |
|---|---|
| `ADMIN` | Lectura y escritura: mantenimiento de usuarios y de la estructura organizacional (y en fases siguientes catálogos) |
| `CONSULTA` | Solo lectura de datos funcionales: inicio con conteos, su propio perfil y listados y detalles de Empresa, Área, Departamento, Sección y Puesto (`LecturaRequeridaMixin`). Recibe 403 en crear, editar, desactivar y reactivar. Nunca ve hashes ni campos de seguridad. Las pantallas de mantenimiento de usuarios son solo de ADMIN, también para GET (en el detalle de un puesto ve nombre de usuario, nombre, rol y estado, sin enlace) |

La autorización se valida **en el servidor**, en tres capas:

1. **Sesión obligatoria global**: `django.contrib.auth.middleware.LoginRequiredMiddleware` (Django 5.1+)
   exige sesión en todas las vistas. Excepciones explícitas con `@login_not_required`: el login (`LoginView`) y
   `/salud/`. Los archivos estáticos no pasan por las vistas de Django. Una vista nueva queda protegida por
   defecto, aunque se olvide agregar un decorador.
2. **Rol por vista**: `cuentas/permisos.py` define `AdminRequeridoMixin` / `LecturaRequeridaMixin` / `RolRequeridoMixin` (vistas de clase)
   y `admin_requerido` / `rol_requerido(...)` (vistas de función). Sin sesión → redirección al login; con sesión
   y otro rol → **403** (`PermissionDenied`, plantilla `403.html`). Toda vista de escritura los usa.
3. **Modelo**: `Usuario.clean()` rechaza asignar un puesto inactivo; `rol` tiene `CHECK (rol IN ('ADMIN','CONSULTA'))`.

Ocultar el enlace "Usuarios" del menú a CONSULTA es solo comodidad: P03 envía POST directos (sin botón) a
crear, editar, desactivar, reactivar y cambiar contraseña, y verifica 403 y que los datos no cambian.

No se usa el sitio `/admin/` de Django ni `is_staff`/`is_superuser` (supuesto S6): el único criterio es `rol`.

## 7. Cuentas de demostración

Comando: `docker compose exec web python manage.py crear_cuentas_demo [--restablecer]`.

- Lee del entorno (`.env`, cargado por `env_file` en `compose.yaml`) `DEMO_ADMIN_USUARIO`, `DEMO_ADMIN_CORREO`,
  `DEMO_ADMIN_PASSWORD`, `DEMO_CONSULTA_USUARIO`, `DEMO_CONSULTA_CORREO`, `DEMO_CONSULTA_PASSWORD` (obligatorias) y
  `DEMO_ADMIN_NOMBRE`, `DEMO_CONSULTA_NOMBRE` (opcionales). Si falta o está vacía una obligatoria, termina con
  código 1 y lista las que faltan, sin crear nada.
- Crea, si no existe, una jerarquía mínima con código `DEMO` en los cinco niveles (empresa, área, departamento,
  sección y puesto) marcada con `es_demo = true`: es un dato nuevo de demostración, no proviene del Excel.
  El puesto es obligatorio para todo usuario (supuesto S4).
- Crea las dos cuentas con hash Argon2, tras pasar los validadores de contraseña. Todo ocurre en una transacción.
- **Idempotente**: si una cuenta ya existe (por usuario, sin distinguir mayúsculas), no la duplica ni cambia su
  contraseña. Con `--restablecer` vuelve a poner la contraseña, el rol y el estado activo según el entorno.
- Las credenciales de `.env.example` son solo de demostración; `.env` no se versiona (`AGENTS.md` §8.1). Si se
  cambian en `.env`, hay que recrear el contenedor (`docker compose up -d`) para que `web` las lea.

## 8. Usuarios existentes al migrar `Usuario.puesto`

`cuentas.0002_usuario_puesto` agrega la columna como NULL y `cuentas.0003_usuario_puesto_obligatorio` la vuelve
NOT NULL. Sobre una base vacía no crea nada. Si ya hay usuarios (p. ej. de pruebas manuales), crea una jerarquía
técnica de transición con código `MIGRACION`, **inactiva** en todos sus niveles, y asigna ahí a esos usuarios: no
se borra, desactiva ni cambia de rol a nadie y siguen pudiendo entrar. Como el puesto está inactivo, no admite
asociaciones nuevas; el administrador debe reasignarlos a un puesto activo desde Usuarios → Editar. Probado en
`tests/test_migracion_puesto.py`.
