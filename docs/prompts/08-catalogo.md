# Prompt 08: Catálogo de servicios

- Herramienta: Claude Code 2.1.288 (modo auto)
- Modelo: Claude Opus 5.5 (cuenta Claude Pro)
- Fecha de uso: 2026-10-02 y 2026-10-03
- Fase: Catálogo
- Commit resultante: `b63b77f`

## Objetivo
Implementar los catálogos de clase, criticidad y tipo, los servicios de nivel 1 y nivel 2, la búsqueda con filtros, la ficha del servicio y la asignación de responsables con sus validaciones.

## Contexto suministrado
Limpié la sesión con `/clear`. Le indiqué leer `modelo-datos.md` (catálogos, servicios, trazabilidad y decisiones D1, D6, D7, D8 y D9), `seguridad.md` y la sección 3.3 del enunciado. Le pedí crear las tablas de trazabilidad pero no el importador todavía.

## Prompt utilizado
```
[PEGAR AQUÍ EL PROMPT 8 COMPLETO]
```

## Seguimiento por corte de conexión
La computadora se suspendió cuando el asistente ya tenía el código y las pruebas en verde y estaba actualizando la documentación, y la sesión dio "API Error: The response stopped arriving". Revisé que la red de la VM funcionara y, sin limpiar la sesión, le pedí:
```
[PEGAR AQUÍ EL MENSAJE DEL PASO 38.2]
```
Revisó con `git status` y `git diff` lo que había alcanzado a cambiar, terminó la documentación y volvió a correr la verificación.

## Extracto de la salida
- Modelos y migraciones de catálogos, nivel 1, nivel 2, mapeo de correcciones y tablas de trazabilidad, con el CHECK de mínimo y máximo en la base.
- Listado de servicios con búsqueda y filtros combinables por nivel 1, estado del registro, ACTIVO del Excel, clase, criticidad, tipo, estado de revisión y sección responsable, con paginación que conserva los filtros.
- Ficha del servicio con todos sus atributos, su nivel 1, responsables, origen y observaciones. Los vacíos se muestran como "Sin dato" o "Desconocido".

Decisiones del asistente que revisé y acepté:
- No se puede desactivar un usuario que sea responsable de un servicio activo. Se rechaza y se listan los servicios, sin quitar asignaciones en silencio (igual que D1).
- Cambiar el puesto de un responsable a otra sección se rechaza siempre, aunque sus servicios estén dados de baja.
- Agregó una regla que yo no había previsto: no se puede mover un puesto a otra sección si alguno de sus usuarios es responsable, porque el usuario cambiaría de sección de forma indirecta.
- Descripción y métrica no se recortan al guardar, para no alterar el texto original de I5.
- El listado de nivel 2 muestra solo los activos por defecto, y el filtro permite ver todos.

Captura: `../evidencias/prompt08-resultado.png`.

## ¿Cumplió el criterio de aceptación?
Sí. `bash scripts/verificar.sh` terminó con código 0 y 111 pruebas aprobadas (log `docs/evidencias/verificacion-20261003-0819.log`), incluidas P03, P05, P09, P10 y P11. No hubo cambios en `data/` ni `.env` versionado.

En el navegador creé un servicio de nivel 2 con mínimo 10 y máximo 5, y el formulario no lo guardó (`../evidencias/prompt08-minimo-maximo.png`). Después desactivé el servicio de prueba T1 para que no se mezclara con los datos del Excel.

## Problemas observados e iteración
No hizo falta revisar el prompt. El único problema fue el corte de conexión, que se resolvió retomando la misma sesión.
