# Prompt 10: Actualización de contexto v3

- Herramienta: Claude Code 2.1.288 (modo auto)
- Modelo: Claude Opus 5.5 (cuenta Claude Pro)
- Fecha de uso: 2026-10-03
- Fase: Context engineering (actualización #2)
- Commit resultante: (se completa después del commit)

## Objetivo
Actualizar `AGENTS.md` con lo que se aprendió al implementar el importador, para que las siguientes sesiones del asistente trabajen con las reglas reales y no con las de v2.

## Contexto suministrado
No limpié la sesión, porque el asistente necesitaba recordar los hallazgos del Prompt 09. Trabajó sobre `AGENTS.md`, `docs/contexto/fases.md` y el código del importador.

## Motivo de la actualización
Al implementar y probar la importación aparecieron casos que no estaban previstos en v2: observaciones que se repetían entre ejecuciones, conflictos entre atributos de un mismo servicio, referencias dadas de baja que bloqueaban la reimportación y el uso de otro archivo con `--archivo`. Si no los registraba en el contexto, un asistente en una sesión nueva podía volver a romper esas reglas.

## Prompt utilizado (10a)
```
[PEGAR AQUÍ EL PROMPT DEL PASO 45.2]
```

## Seguimientos (10b y 10c)
El asistente encontró dos frases desactualizadas en `AGENTS.md`: §10 decía que `verificar.sh` estaba pendiente y §8.3 hablaba del script de reinicio "cuando exista". Le pedí corregirlas:
```
[PEGAR AQUÍ EL MENSAJE DE §10]
```
```
[PEGAR AQUÍ EL MENSAJE DE §8.3]
```

## Extracto de la salida
- §5 con siete reglas nuevas: huella de observaciones, `CONFLICTO_ATRIBUTOS`, criterio de `PENDIENTE_REVISION`, precisión de S7, `REFERENCIA_INACTIVA`, reglas del hash y por qué SE.11 no genera observación. Antes de escribir cada regla, el asistente la comprobó en `src/importacion/importador.py`.
- §7 con las opciones reales de `importar_catalogo`, `importar.sh` y `cargar_demo`.
- §10 con los 7 pasos de `verificar.sh` como definición de terminado.
- §8.3 actualizado con el script de reinicio y su confirmación "BORRAR".
- Fila v3 en el registro de cambios y `fases.md` con las fases 4 a 8 realizadas.

Captura: `../evidencias/prompt10-contexto-v3.png`.

## ¿Cumplió el criterio de aceptación?
Sí. `grep -n "v3" AGENTS.md` muestra la fila del registro y la sección de reglas nuevas. `AGENTS.md` quedó en 207 líneas, y el `grep` de "pendiente" y "cuando exista" solo encuentra usos correctos (`PENDIENTE_REVISION` y P12, que todavía no estaba hecha).

## Problemas observados e iteración
No hizo falta revisar el prompt. Los dos seguimientos fueron para corregir partes del contexto que se habían quedado viejas, cosa que el asistente notó por su cuenta.
