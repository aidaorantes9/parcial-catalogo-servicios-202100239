# Prompt 06: Autenticación, usuarios y modelos de organización

- Herramienta: Claude Code 2.1.288 (modo auto)
- Modelo: Claude Opus 5.5 (cuenta Claude Pro)
- Fecha de uso: 2026-10-02
- Fase: Autenticación
- Commit resultante: `aaae9a8`

## Objetivo
Implementar inicio y cierre de sesión local, roles ADMIN y CONSULTA validados en el servidor, mantenimiento de usuarios, los modelos de la jerarquía organizacional y un comando para crear las cuentas de evaluación.

## Contexto suministrado
Sesión nueva después de actualizar Claude Code, así que arrancó solo con `AGENTS.md`. Le indiqué leer `docs/contexto/modelo-datos.md` y las secciones 3.1 y 3.2 del enunciado.

Cambié el orden que tenía planeado: las cuentas demo necesitan un puesto y el puesto depende de la jerarquía, así que en este prompt pedí también los modelos de organización. Las pantallas de organización quedaron para el siguiente.

## Prompt utilizado
```
OBJETIVO
Implementar autenticación local, autorización por roles en el servidor, mantenimiento de usuarios y los modelos de la estructura organizacional.

CONTEXTO
Lee AGENTS.md (ya cargado), docs/contexto/modelo-datos.md (organización y usuario) y la sección 3.1 y 3.2 de docs/contexto/enunciado.md.

INSTRUCCIONES
1. Modelos y migraciones de Empresa, Area, Departamento, Seccion y Puesto según modelo-datos.md (códigos únicos dentro del padre, Empresa con código único global, activo para baja lógica). Agrega a Usuario el campo puesto según el supuesto S4. Como la base de evaluación puede tener datos de pruebas manuales, la migración debe funcionar sobre una base vacía y explicar qué pasa si ya existen usuarios.
2. Login con usuario O correo y contraseña, validado contra la base (backend de autenticación propio, comparación sin distinguir mayúsculas). Sin proveedores externos. Mensaje de error genérico que no revele si el usuario existe.
3. Logout solo por POST, que invalide la sesión en el servidor (flush). Después del logout, la cookie anterior no debe dar acceso.
4. Usuario inactivo: no puede iniciar sesión, y si se desactiva con la sesión abierta, su siguiente petición debe ser rechazada y su sesión cerrada.
5. Roles ADMIN y CONSULTA con mixins o decoradores reutilizables:
   - Todo requiere sesión excepto login, /salud/ y archivos estáticos.
   - Toda operación de escritura (crear, editar, desactivar) exige ADMIN y responde 403 a CONSULTA aunque la petición se haga directo, sin botón.
   - CONSULTA puede leer datos funcionales, pero nunca ve hashes ni campos de seguridad.
6. Mantenimiento de usuarios (solo ADMIN): listado paginado con búsqueda, detalle, crear con contraseña (validadores de Django), editar nombre, correo, rol y puesto, desactivar y reactivar (baja lógica), cambiar contraseña. El puesto debe estar activo. Nunca se muestra el hash. Un administrador no puede desactivarse a sí mismo.
7. Plantilla base con menú según rol, nombre del usuario y botón de cerrar sesión (formulario POST). Interfaz simple y limpia.
8. Comando `python manage.py crear_cuentas_demo`: lee DEMO_ADMIN_USUARIO, DEMO_ADMIN_CORREO, DEMO_ADMIN_PASSWORD, DEMO_CONSULTA_USUARIO, DEMO_CONSULTA_CORREO y DEMO_CONSULTA_PASSWORD del entorno; crea si no existe una jerarquía DEMO mínima (empresa, área, departamento, sección y puesto marcados como datos de demostración) y las dos cuentas. Idempotente: si ya existen, no las duplica ni cambia su contraseña salvo con --restablecer. Si falta una variable, falla con mensaje claro y código distinto de 0. Actualiza .env.example si hace falta.
9. Pruebas en tests/ con marcadores de pytest p01, p02 y p03 (regístralos en pytest.ini) y docstring con el ID:
   - P01: login válido con usuario y con correo; login inválido rechazado con contraseña incorrecta y con usuario inexistente.
   - P02: sin sesión se rechaza el acceso a páginas y operaciones protegidas; tras logout la sesión anterior ya no sirve; usuario inactivo no puede entrar y su sesión abierta se invalida.
   - P03: CONSULTA recibe 403 al hacer POST de crear, editar y desactivar usuarios; GET de páginas de lectura permitido; CONSULTA no puede ver el hash de ningún usuario.
   - Prueba de crear_cuentas_demo: idempotencia y error si falta una variable.
10. Crea docs/contexto/seguridad.md: algoritmo de hash y por qué, manejo y cierre de sesión, usuarios inactivos, protección CSRF, roles y dónde se valida, y cómo se crean las cuentas demo. Agrégalo al mapa de documentos de AGENTS.md y actualiza la tabla de comandos (§7), sin nueva fila en el registro de cambios.

RESTRICCIONES
- No pongas credenciales reales en ningún archivo; los valores de .env.example son de demostración.
- Ocultar botones no cuenta como autorización.
- No uses `down -v`. No hagas commit.

SALIDA ESPERADA
Código, migraciones, plantillas, comando, pruebas, docs/contexto/seguridad.md y la salida real de `bash scripts/verificar.sh`.

CRITERIO DE ACEPTACIÓN
`bash scripts/verificar.sh` termina con código 0 con P01, P02 y P03 en verde, y `docker compose exec web python manage.py crear_cuentas_demo` se puede ejecutar dos veces sin error ni duplicados.
```

## Extracto de la salida
- Backend de autenticación propio que acepta usuario o correo sin distinguir mayúsculas. El mismo mensaje de error para usuario inexistente, contraseña incorrecta o cuenta inactiva.
- Sesión obligatoria con un middleware; solo el login y `/salud/` quedan abiertos.
- Logout solo por POST que borra la sesión en el servidor. Si se desactiva a un usuario con la sesión abierta, su siguiente petición se rechaza.
- `AdminRequeridoMixin` y `admin_requerido` en `cuentas/permisos.py`. Sin sesión redirige al login y con rol CONSULTA responde 403.
- Mantenimiento de usuarios, página "Mi perfil" y comando `crear_cuentas_demo` con la opción `--restablecer`.
- `docs/contexto/seguridad.md` nuevo y AGENTS.md actualizado (mapa de documentos y comandos).

Decisiones del asistente que revisé:
- CONSULTA no puede ver la lista de usuarios. Lo acepté, porque el enunciado le da lectura de los datos funcionales (organización y catálogo) y los usuarios son parte de la administración.
- Por su cuenta agregó que un administrador no pueda quitarse su propio rol ADMIN. Lo acepté, porque evita quedarse sin administradores.
- Agregó el campo `es_demo` para marcar la jerarquía de demostración y la variable opcional `COOKIES_SEGURAS` para HTTPS.
- Cambió una contraseña de las pruebas porque el validador de Django la rechazó por parecerse al usuario.

Captura: `../evidencias/prompt06-resultado.png`.

## ¿Cumplió el criterio de aceptación?
Sí. `bash scripts/verificar.sh` terminó con código 0 y 44 pruebas aprobadas (log `docs/evidencias/verificacion-20261002-1921.log`). `crear_cuentas_demo` se ejecutó dos veces sin duplicar nada, y sin una variable falla con código 1.

El asistente dijo que no probó el login en el navegador porque para eso tenía que leer `.env`. Lo probé yo en Firefox:
- Contraseña incorrecta: mensaje genérico (`../evidencias/prompt06-login-invalido.png`).
- Admin: ve la lista de usuarios (`../evidencias/prompt06-admin-usuarios.png`).
- Consulta entrando a mano a `/usuarios/`: Acceso denegado 403 (`../evidencias/prompt06-consulta-403.png`).

## Problemas observados e iteración
No hizo falta revisar el prompt. Al terminar, Claude Code sugirió una respuesta automática para dividir los commits; no la usé e hice un solo commit porque fue un solo prompt.

