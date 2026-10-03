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
[PEGAR AQUÍ EL PROMPT 6 COMPLETO]
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

