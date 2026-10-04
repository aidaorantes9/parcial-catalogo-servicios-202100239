# Catálogo de servicios de TI

Aplicación web que sistematiza el catálogo de servicios de TI del archivo `data/CatalogoServicios.xlsx`, con
usuarios, roles (administrador y consulta) y estructura organizacional (Empresa, Área, Departamento, Sección,
Puesto y Usuario). Está hecha con Django 5.2 y PostgreSQL 16 y se ejecuta completa con Docker Compose.

La explicación de cómo resolví el parcial, las decisiones, la matriz de requisitos y los resultados de pruebas
están en [docs/RESOLUCION.md](docs/RESOLUCION.md).

## Integrante

| Nombre | Carné |
|---|---|
| Aída Alejandra Mansilla Orantes | 202100239 |

Repositorio: https://github.com/aidaorantes9/parcial-catalogo-servicios-202100239 (rama `main`).

## Requisitos

Todo se ejecuta dentro de contenedores. En el equipo anfitrión no hace falta instalar Python, Django ni
PostgreSQL.

| Herramienta | Mínimo recomendado | Versión con la que lo probé |
|---|---|---|
| Docker Engine | 24 o superior | 29.1.3 |
| Docker Compose | v2.20 o superior (plugin `docker compose`, no el antiguo `docker-compose`) | 2.40.3 |
| Git | cualquier versión reciente | 2.43 |
| Bash y `sha256sum` (coreutils) | los que trae Linux | Linux Mint 22.3 |

Los scripts usan `docker compose up --wait` y `depends_on` con `condition: service_healthy`, por eso pido
Compose v2. Solo lo probé con las versiones de la tercera columna, en Linux Mint 22.3 dentro de VirtualBox; no
lo probé en versiones anteriores ni en Windows o macOS.

El puerto 8000 del anfitrión debe estar libre.

## 1. Clonar y configurar

```bash
git clone https://github.com/aidaorantes9/parcial-catalogo-servicios-202100239.git
cd parcial-catalogo-servicios-202100239
cp .env.example .env
```

`.env.example` solo tiene valores de demostración. `.env` está en `.gitignore` y nunca se versiona. Antes de
levantar, revisé y recomiendo revisar estas variables en `.env`:

| Variable | Para qué sirve |
|---|---|
| `SECRET_KEY` | Clave de Django. Si falta, la aplicación no arranca. Conviene cambiar el valor de ejemplo |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Base de datos de evaluación. Las pruebas usan otra base, `test_<POSTGRES_DB>` |
| `ALLOWED_HOSTS` | Por defecto `localhost,127.0.0.1` |
| `DEBUG` | `0` por defecto |
| `COOKIES_SEGURAS` | `0` en local (HTTP). Ponerlo en `1` solo si se sirve por HTTPS |
| `DEMO_ADMIN_USUARIO`, `DEMO_ADMIN_CORREO`, `DEMO_ADMIN_PASSWORD`, `DEMO_ADMIN_NOMBRE` | Cuenta de evaluación con rol administrador |
| `DEMO_CONSULTA_USUARIO`, `DEMO_CONSULTA_CORREO`, `DEMO_CONSULTA_PASSWORD`, `DEMO_CONSULTA_NOMBRE` | Cuenta de evaluación con rol consulta |
| `DEMO_RESPONSABLE_PASSWORD` (opcional, comentada) | Contraseña de los dos usuarios responsables que crea `cargar_demo`. Si no se define, se crean con contraseña inutilizable |

Las contraseñas de demostración deben pasar los validadores de Django (mínimo 8 caracteres, no comunes y no
parecidas al usuario). Si se cambia `.env` con los servicios ya levantados, hay que recrear el contenedor con
`docker compose up -d --wait` para que `web` lea los valores nuevos.

## 2. Levantar, importar y cargar datos (en este orden)

Todos los comandos se ejecutan desde la raíz del repositorio.

```bash
# 2.1 Construir y levantar db y web; espera a que ambos estén healthy
docker compose up --build -d --wait

# 2.2 (Opcional) Migraciones: el entrypoint de web ya las aplica al arrancar
docker compose exec web python manage.py migrate

# 2.3 Importar el Excel original (comprueba el SHA-256 y los controles 12/46)
bash scripts/importar.sh

# 2.4 Crear las cuentas de evaluación (admin y consulta) y la jerarquía DEMO mínima
docker compose exec web python manage.py crear_cuentas_demo

# 2.5 Cargar la organización de demostración y 4 asignaciones de responsables (requiere el paso 2.3)
docker compose exec web python manage.py cargar_demo
```

El enunciado pide que funcione `docker compose up --build -d`; también funciona, pero sin `--wait` el comando
regresa antes de que la aplicación esté lista. Por eso uso `--wait`.

Qué esperar:

- `importar.sh` muestra el resumen de la importación y termina con `Código de salida: 0`, con
  `Códigos de nivel 1: 12 / esperado 12 → PASA` y `Códigos de nivel 2: 46 / esperado 46 → PASA`. Guarda la
  salida en `docs/evidencias/importacion-AAAAMMDD-HHMM.log`. Opciones: `--dry-run` (no guarda nada),
  `--archivo RUTA`, `--sha256 RUTA_SUMA` y `--exigir-controles`.
- Repetir `bash scripts/importar.sh` no duplica registros: la segunda vez da 0 creados y 0 actualizados.
- `crear_cuentas_demo` y `cargar_demo` son idempotentes. `crear_cuentas_demo --restablecer` vuelve a poner la
  contraseña, el rol y el estado activo de las dos cuentas según `.env`.

## 3. Abrir la aplicación

- URL: http://127.0.0.1:8000/ (también http://localhost:8000/). Sin sesión redirige a `/entrar/`.
- El puerto está publicado solo en `127.0.0.1` (`127.0.0.1:8000:8000` en `compose.yaml`), así que la aplicación
  no es accesible desde otros equipos de la red.
- Comprobación de salud sin sesión: http://127.0.0.1:8000/salud/

### Cuentas de evaluación

Se entra con el usuario **o** con el correo, más la contraseña. Los valores son los de las variables
`DEMO_ADMIN_*` y `DEMO_CONSULTA_*` de tu `.env`; si no los cambiaste, son los de demostración que aparecen en
[.env.example](.env.example). No los repito aquí a propósito.

| Rol | Variables | Qué puede hacer |
|---|---|---|
| Administrador | `DEMO_ADMIN_USUARIO` o `DEMO_ADMIN_CORREO`, `DEMO_ADMIN_PASSWORD` | Mantenimiento de usuarios, organización, catálogos y servicios; historial de importaciones |
| Consulta | `DEMO_CONSULTA_USUARIO` o `DEMO_CONSULTA_CORREO`, `DEMO_CONSULTA_PASSWORD` | Solo lectura de organización y catálogo; recibe 403 en cualquier escritura |

Pantallas principales: `/organizacion/empresas/` (y `areas`, `departamentos`, `secciones`, `puestos`),
`/catalogo/servicios/` (búsqueda, filtros y ficha), `/catalogo/nivel1/`, `/catalogo/clases/`,
`/catalogo/criticidades/`, `/catalogo/tipos/`, `/usuarios/` (solo admin) e `/importacion/ejecuciones/` (solo
admin). El cierre de sesión es el botón "Cerrar sesión" del menú (envía un POST a `/salir/`).

## 4. Pruebas

```bash
# Todas las pruebas de pytest (P01 a P11 y casos extra), en la base aislada test_*
bash scripts/pruebas.sh

# Un escenario por su marcador: p01 ... p11
bash scripts/pruebas.sh -m p06

# Varios escenarios
bash scripts/pruebas.sh -m "p06 or p07 or p08"

# P12: persistencia (reinicia los contenedores sin borrar el volumen)
bash scripts/prueba_persistencia.sh      # equivalente: bash scripts/pruebas.sh -m p12
```

- Las pruebas de pytest corren dentro del contenedor `web` sobre la base `test_<POSTGRES_DB>`, que se crea y se
  destruye en cada sesión. No tocan la base de evaluación.
- P12 sí usa la base de evaluación: necesita los servicios levantados y el catálogo importado (pasos 2.1 y 2.3).
  Crea una empresa marcador `P12-AAAAMMDDHHMMSS`, ejecuta `docker compose down` **sin** `-v` y
  `docker compose up -d --wait`, comprueba que el marcador, los conteos y el volumen siguen igual y al final da de
  baja el marcador (no lo borra). Log en `docs/evidencias/persistencia-AAAAMMDD-HHMM.log`.
- Marcadores extra: `humo`, `catalogo`, `importacion`, `demo`.
- Qué cubre cada escenario y de qué tipo es cada prueba: [docs/contexto/matriz-pruebas.md](docs/contexto/matriz-pruebas.md).

## 5. Verificación completa

```bash
# Verificación normal (definición de terminado del proyecto)
bash scripts/verificar.sh

# Verificación completa: lo anterior más la prueba de persistencia P12 al final
bash scripts/verificar.sh --completo
```

`verificar.sh` necesita `.env` y ejecuta en orden, deteniéndose en el primer fallo: `docker compose config`,
`docker compose up --build -d --wait`, revisión de los logs de `web` (sin `[ERROR]`, `Traceback` ni
`CRITICAL`), `ruff check`, `ruff format --check`, `makemigrations --check --dry-run`, `sha256sum -c` del Excel y
`pytest`. Imprime `PASA` o `FALLA` por paso, termina con código 0 solo si todo pasa y guarda la salida en
`docs/evidencias/verificacion-AAAAMMDD-HHMM.log`. En mis logs, solo la etapa de pytest tardó entre 85 y 267
segundos.

Otros comandos útiles:

```bash
# Comprobar que el Excel original no cambió
sha256sum -c data/CatalogoServicios.xlsx.sha256

# Lint
docker compose exec web ruff check --no-cache .
docker compose exec web ruff format --check --no-cache .

# Análisis de solo lectura del Excel (sale 0 si los controles 12/46 pasan)
docker run --rm -v "$PWD":/w -w /w python:3.12-slim sh -c "pip install -q openpyxl && python scripts/analizar_excel.py"
```

## 6. Operación del entorno

```bash
# Estado de los servicios
docker compose ps

# Logs (seguir en vivo con -f)
docker compose logs -f web
docker compose logs db

# Detener sin perder datos (los contenedores se eliminan, el volumen datos_postgres se conserva)
docker compose down

# Volver a levantar con los mismos datos
docker compose up -d --wait
```

`docker compose stop` y `docker compose start` también conservan los datos. Los dos servicios tienen
`restart: unless-stopped`, así que vuelven a arrancar solos si se reinicia Docker.

### Reinicio destructivo (solo para datos de prueba)

> **Advertencia:** esto borra el volumen de PostgreSQL. Se pierden usuarios, organización, catálogo importado,
> asignaciones e historial de importaciones, y no se puede deshacer.

```bash
bash scripts/reiniciar_datos_prueba.sh
```

El script pide escribir `BORRAR` para confirmar; con cualquier otra respuesta no borra nada. Es el único lugar
del proyecto donde se usa `docker compose down -v`. Después hay que repetir la sección 2 completa.

## 7. Estructura del repositorio

| Ruta | Contenido |
|---|---|
| `src/` | Proyecto Django: `config/` (ajustes y URLs), apps `cuentas`, `organizacion`, `catalogo`, `importacion`, y `templates/` |
| `tests/` | Pruebas de pytest (P01 a P11 y casos extra); se montan en el contenedor en solo lectura |
| `scripts/` | `verificar.sh`, `pruebas.sh`, `importar.sh`, `prueba_persistencia.sh`, `reiniciar_datos_prueba.sh` y `analizar_excel.py` |
| `data/` | `CatalogoServicios.xlsx` original (sin modificar) y su `CatalogoServicios.xlsx.sha256` |
| `docker/entrypoint.sh` | Espera a PostgreSQL, aplica migraciones y recopila estáticos antes de iniciar gunicorn |
| `Dockerfile`, `compose.yaml`, `.dockerignore`, `.env.example` | Configuración de Docker y variables de ejemplo |
| `AGENTS.md`, `CLAUDE.md` | Contexto y reglas para el asistente de IA |
| `docs/RESOLUCION.md` | Documento de resolución del parcial |
| `docs/contexto/` | Enunciado, análisis del Excel, modelo de datos, mapeo, seguridad, matriz de pruebas y fases |
| `docs/prompts/` | Registro de los prompts usados, con su plantilla |
| `docs/evidencias/` | Logs de verificación, importación y persistencia, y capturas |
