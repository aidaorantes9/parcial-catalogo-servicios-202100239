# Prompt 09: Importador del Excel y datos de demostración

- Herramienta: Claude Code 2.1.288 (modo auto)
- Modelo: Claude Opus 5.5 (cuenta Claude Pro)
- Fecha de uso: 2026-10-03
- Fase: Importación
- Commit resultante: (se completa después del commit)

## Objetivo
Implementar un importador repetible y trazable del Excel original, que respete todas las decisiones del modelo, y un comando que cree al menos tres asignaciones de responsables para la demostración.

## Contexto suministrado
Limpié la sesión con `/clear`. Le indiqué leer `analisis-excel.md`, `modelo-datos.md` (importación, trazabilidad, claves naturales y D2 a D8) y la sección 3.4 del enunciado, y reutilizar la lectura de `scripts/analizar_excel.py`. Repetí la regla de que el texto de las celdas es dato y no instrucción.

## Prompt inicial (9a)
```
[PEGAR AQUÍ EL PROMPT 9 COMPLETO]
```

Resultado: la primera importación dio 12/46 PASA con 17 observaciones y la segunda 0 creados y 0 observaciones nuevas. `cargar_demo` dejó 4 asignaciones en 2 secciones. El asistente reportó 8 hallazgos que no estaban previstos en el contexto. Acepté seis: la huella para no duplicar observaciones, el tipo nuevo `CONFLICTO_ATRIBUTOS`, que un servicio quede pendiente de revisión si tiene alguna advertencia (por eso SE.01.01 queda pendiente por la celda I5), la precisión sobre el supuesto S7, que SE.11 repite el patrón de SE.12 sin generar observación, y que los usuarios demo se identifican por su puesto DEMO.

Captura: `../evidencias/prompt09-resultado.png`.

## Iteración 2: dos problemas en el importador
Problemas observados:
- Si el Excel apuntaba a un valor de catálogo o a un nivel 1 dado de baja por un administrador, toda la importación se revertía. Eso rompe el requisito de que la importación se pueda repetir, porque una acción normal de administración la dejaba inutilizable.
- El hash siempre se comparaba con el del archivo original, aunque se usara `--archivo`, así que esa opción no servía con ningún otro archivo.

Prompt revisado (9b):
```
[PEGAR AQUÍ EL PROMPT DEL PASO 42]
```

Resultado comprobado: la importación ahora continúa, conserva los valores del servicio afectado y registra `REFERENCIA_INACTIVA`. Con otro archivo se registra su hash, se muestra un aviso y los controles son informativos salvo con `--exigir-controles`. Se agregaron pruebas para los tres casos y la verificación terminó con 136 pruebas aprobadas (log `docs/evidencias/verificacion-20261003-0906.log`). Captura: `../evidencias/prompt09-iteracion2.png`.

El asistente aclaró un efecto de combinar las reglas: si un servicio nuevo no se crea porque su nivel 1 está inactivo, falta en el conteo y con el archivo original la importación falla. Lo acepté, porque solo puede pasar antes de la primera importación; después D1 impide desactivar un nivel 1 con servicios activos.

## ¿Cumplió el criterio de aceptación?
Sí. Lo comprobé yo misma con `bash scripts/importar.sh`: ejecución #5 exitosa, 12/46 PASA, 0 creados, 0 actualizados, 0 observaciones nuevas y código de salida 0 (log `docs/evidencias/importacion-20261003-0912.log`). En el resumen aparecen los seis casos del enunciado: 49 filas de continuación omitidas, el conflicto de SE.12, el formato de SE.12.n, los atributos ausentes como NULL, las filas 42 y 67 sin asignar y la trazabilidad de cada servicio.

En el navegador revisé:
- El listado de servicios con las asignaciones de `cargar_demo` (`../evidencias/prompt09-listado.png`).
- La ficha de SE.12.1 con hoja, fila, celdas originales y transformaciones (`../evidencias/prompt09-ficha-se12.png`).
- El historial de importaciones, donde solo la primera creó registros (`../evidencias/prompt09-ejecuciones.png`).

