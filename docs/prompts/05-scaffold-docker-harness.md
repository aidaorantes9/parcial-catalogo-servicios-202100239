# Prompt 05: Scaffold, Docker y harness base

- Herramienta: Claude Code 2.1.287 (modo auto)
- Modelo: Claude Opus 5.5 (cuenta Claude Pro)
- Fecha de uso: 2026-10-02
- Fase: Scaffold y Docker / Harness engineering
- Commit resultante: `7ddcb3f`

## Objetivo
Crear el esqueleto del proyecto en Django, la configuración de Docker Compose y los scripts que permiten verificar el proyecto con un solo comando.

## Contexto suministrado
Antes de este prompt limpié la sesión con `/clear`. El asistente arrancó solo con `AGENTS.md` (cargado desde `CLAUDE.md`) y le indiqué leer `docs/contexto/modelo-datos.md`. Lo hice así para comprobar que el contexto versionado era suficiente y que no dependía del historial del chat.

## Prompt utilizado (5a)
```
[PEGAR AQUÍ EL PROMPT 5 DEL PASO 24.3]
```

## Iteración 1: conflicto entre el prompt y el contexto
Problema observado: en mi prompt pedí que el usuario heredara de `AbstractUser`, pero en el modelo de datos v2 yo había aceptado el supuesto S6, que define `AbstractBaseUser` sin `is_staff` ni `is_superuser` y con la autorización basada solo en el rol. El asistente no siguió el prompt a ciegas: detectó la contradicción y me preguntó cuál usar.

Prompt revisado: le indiqué usar `AbstractBaseUser` (opción 1), para ser coherente con S6 y no tener que mantener `is_staff` sincronizado con el rol.

Resultado comprobado: la migración `cuentas.0001_initial` creó el usuario con `username`, `email`, `nombre`, `rol` e `is_active`, con restricciones de unicidad sin distinguir mayúsculas. Captura: `../evidencias/prompt05-conflicto-usuario.png`.

Lo que aprendí: el prompt tenía un error mío y el contexto versionado sirvió para detectarlo.

## Incidente durante la ejecución
Mientras el asistente levantaba los servicios, la computadora se suspendió y la máquina virtual perdió el DNS. El comando `docker compose up --wait` quedó esperando más de 5 horas. Al revisar los logs vi que la aplicación sí había arrancado bien. Reinicié `systemd-resolved` y `NetworkManager`, y el asistente continuó solo.

## Extracto de la salida
- Proyecto Django 5.2 en `src/` con las apps `cuentas`, `organizacion`, `catalogo` e `importacion`.
- `Dockerfile` con usuario no root, `compose.yaml` con PostgreSQL 16, volumen, healthchecks y espera de la base.
- Contraseñas con Argon2. Si falta `SECRET_KEY`, la app no arranca y muestra un mensaje claro.
- Scripts `verificar.sh`, `pruebas.sh` y `reiniciar_datos_prueba.sh` (el único con `down -v`, con confirmación).
- Pruebas de humo para `/` y `/salud/`. Las pruebas usan una base aparte que empieza con `test_`.
- El puerto queda publicado solo en `127.0.0.1:8000`.

Captura: `../evidencias/prompt05-resultado.png`.

## Seguimiento 5b: ciclo de harness con un fallo real
Al revisar los logs del contenedor vi `[ERROR] Control server error: Permission denied: '/home/app'`. `verificar.sh` no lo había detectado porque no revisaba los logs. Le pedí al asistente agregar ese control, ejecutarlo antes de corregir, corregir la causa y volver a ejecutar.

```
[PEGAR AQUÍ EL PROMPT DEL CICLO DE HARNESS DEL PASO 26]
```

Resultado: el control nuevo falló como esperaba. La causa era que el Dockerfile creaba el usuario `app` con `--no-create-home` y gunicorn no podía crear su socket de control. Se cambió a `--create-home` y la verificación volvió a terminar con código 0. En el proceso el asistente encontró otro problema en el script: dos ejecuciones en el mismo minuto se mezclaban en el mismo log. Lo corrigió agregando un sufijo al nombre. El fallo no fue introducido a propósito.

Detalle completo: `../evidencias/ciclo-harness/README.md`, `01-fallo.log` y `02-exito.log`. Capturas: `../evidencias/ciclo-harness-fallo.png` y `../evidencias/ciclo-harness-exito.png`.

## ¿Cumplió el criterio de aceptación?
Sí. Lo comprobé yo misma ejecutando `bash scripts/verificar.sh`: los 8 pasos en PASA, 3 pruebas aprobadas y código de salida 0. El log está en `docs/evidencias/verificacion-20261002-1902.log`.
