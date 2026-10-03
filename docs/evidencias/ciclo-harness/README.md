# Ciclo de harness: error del socket de control de gunicorn

Fecha: 2026-10-02. Commit base: `d10c972` (scaffold sin commitear encima).

> El fallo **no** fue introducido deliberadamente. Apareció en los logs del contenedor `web` generado por el
> scaffold (prompt 05), en una ejecución en la que `scripts/verificar.sh` terminaba con código 0.

## 1. Tarea

Al revisar los logs del contenedor `web` encontramos esta línea:

```
[ERROR] Control server error: [Errno 13] Permission denied: '/home/app'
```

`scripts/verificar.sh` no la detectó porque no revisaba los logs: el contenedor quedaba `healthy` y todas las
pruebas pasaban. La tarea fue hacer que el harness detectara este tipo de fallo y luego corregir la causa.

## 2. Cambio en el control

Agregamos a `scripts/verificar.sh`, justo después de levantar los servicios, el paso **"logs de web sin errores"**:

- Obtiene la hora del último arranque del contenedor (`docker inspect -f '{{.State.StartedAt}}'`).
- Revisa `docker compose logs --since <arranque> web`.
- Falla si encuentra líneas con `[ERROR]`, `Traceback` o `CRITICAL`, y las muestra.

## 3. Control ejecutado y fallo detectado

Ejecutamos `bash scripts/verificar.sh` **sin corregir** la causa. Terminó con código 1 en el paso nuevo
(log completo: [`01-fallo.log`](01-fallo.log)):

```
PASA: docker compose config
PASA: construir y levantar servicios (healthy)
---- logs de web sin errores ----
Revisando logs de web desde 2026-10-03T00:57:27.15206902Z
Líneas con errores en los logs de web:
web-1  | [2026-10-03 00:57:36 +0000] [1] [ERROR] Control server error: [Errno 13] Permission denied: '/home/app'
FALLA: logs de web sin errores (código 1)
```

## 4. Causa raíz

- gunicorn 26 (fijado en `requirements.txt`) abre por defecto un **socket de control** en
  `$HOME/.gunicorn/gunicorn.ctl`. Lo comprobamos con `gunicorn --help`, que muestra
  `--control-socket PATH ... [/home/app/.gunicorn/gunicorn.ctl]`.
- En el `Dockerfile` creamos el usuario no root con `useradd --no-create-home`. Su `HOME` es `/home/app`, pero
  ese directorio no existía (`ls: cannot access '/home/app'`).
- Al intentar crear `/home/app/.gunicorn`, gunicorn necesita escribir en `/home`, que pertenece a root. El
  usuario `app` no tiene permiso, de ahí `Errno 13`.
- El servidor HTTP siguió funcionando, por eso el healthcheck y las pruebas pasaban y el error solo se veía en
  los logs.

## 5. Corrección

En el `Dockerfile` cambiamos `--no-create-home` por `--create-home`, de modo que `/home/app` existe y pertenece a
`app`. No desactivamos el socket de control (`--no-control-socket`) ni ocultamos el mensaje, y el paso del
control quedó igual de estricto.

Comprobación dentro del contenedor:

```
$ docker compose exec -T web ls -la /home/app/.gunicorn
srw------- 1 app app    0 Oct  3 00:59 gunicorn.ctl
```

El socket se crea con permisos `0600` y pertenece a `app`.

## 6. Hallazgo adicional del propio harness

La primera ejecución después de la corrección (18:57:45) cayó en el mismo minuto que la ejecución fallida
(18:57:16). Como el nombre del log solo llega a minutos y `tee -a` agregaba al final del archivo, las dos
ejecuciones quedaron mezcladas en `docs/evidencias/verificacion-20261002-1857.log`. `01-fallo.log` se copió
antes, así que solo contiene la ejecución fallida.

Corregimos `scripts/verificar.sh`: si el archivo del minuto ya existe, agrega un sufijo (`-2`, `-3`, ...) y
escribe sin `-a`. Así cada log contiene una sola ejecución.

## 7. Nueva ejecución satisfactoria

Volvimos a ejecutar `bash scripts/verificar.sh`, que terminó con **código 0** (log completo:
[`02-exito.log`](02-exito.log), una sola ejecución):

```
PASA: docker compose config
PASA: construir y levantar servicios (healthy)
PASA: logs de web sin errores
PASA: ruff check
PASA: ruff format --check
PASA: migraciones al día (makemigrations --check --dry-run)
PASA: SHA-256 del Excel sin cambios
PASA: pytest
== RESULTADO: PASA (todos los pasos) ==
```

Restricciones respetadas: no usamos `docker compose down -v` y no hicimos commit.
