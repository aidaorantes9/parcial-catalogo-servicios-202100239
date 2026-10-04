# Prompt 10: Actualización de contexto v3

- Herramienta: Claude Code 2.1.288 (modo auto)
- Modelo: Claude Opus 5.5 (cuenta Claude Pro)
- Fecha de uso: 2026-10-03
- Fase: Context engineering (actualización #2)
- Commit resultante: `7e74e30`

## Objetivo
Actualizar `AGENTS.md` con lo que se aprendió al implementar el importador, para que las siguientes sesiones del asistente trabajen con las reglas reales y no con las de v2.

## Contexto suministrado
No limpié la sesión, porque el asistente necesitaba recordar los hallazgos del Prompt 09. Trabajó sobre `AGENTS.md`, `docs/contexto/fases.md` y el código del importador.

## Motivo de la actualización
Al implementar y probar la importación aparecieron casos que no estaban previstos en v2: observaciones que se repetían entre ejecuciones, conflictos entre atributos de un mismo servicio, referencias dadas de baja que bloqueaban la reimportación y el uso de otro archivo con `--archivo`. Si no los registraba en el contexto, un asistente en una sesión nueva podía volver a romper esas reglas.

## Prompt utilizado (10a)
```
OBJETIVO
Actualizar el contexto del proyecto con lo aprendido al implementar el importador (actualización de contexto v3).

INSTRUCCIONES
1. En AGENTS.md §5 (reglas de importación), incorpora como reglas breves los hallazgos aceptados que no estaban en v2:
   - Observaciones deduplicadas por huella entre ejecuciones.
   - Tipo CONFLICTO_ATRIBUTOS para conflictos entre atributos de un mismo servicio.
   - Un servicio queda en PENDIENTE_REVISION si tiene alguna observación de advertencia o error (por eso SE.01.01 queda pendiente por la celda I5).
   - Precisión de S7: el código de nivel 2 y el orden de los valores de catálogo solo se escriben al crearlos.
   - Referencias inactivas: la importación continúa, el servicio conserva sus valores y se registra REFERENCIA_INACTIVA.
   - Hash: obligatorio con el archivo original; con --archivo se registra el hash, se avisa y los controles son informativos salvo con --exigir-controles.
   - SE.11 repite el patrón de nombre de SE.12 pero no genera observación: el conflicto de SE.12 se define por dos valores distintos en la columna B, no por la coincidencia con un hijo.
2. Revisa que la tabla de comandos (§7) tenga importar_catalogo, scripts/importar.sh y cargar_demo con sus opciones reales.
3. Agrega al registro de cambios la fila: "v3 – 2026-10-03 – reglas del importador – al implementar y probar la importación aparecieron casos no previstos en v2 (observaciones repetidas entre ejecuciones, conflictos de atributos, referencias dadas de baja que bloqueaban la reimportación y uso de otro archivo con --archivo)".
4. Actualiza docs/contexto/fases.md marcando como realizadas las fases de scaffold, autenticación, organización, catálogo e importación, con los documentos que se usaron en cada una.
5. Mantén AGENTS.md por debajo de ~250 líneas.

RESTRICCIONES
Solo documentación. No hagas commit.

SALIDA ESPERADA
Resumen de los cambios y la salida de:
grep -n "v3" AGENTS.md
wc -l AGENTS.md
```

## Seguimientos (10b y 10c)
El asistente encontró dos frases desactualizadas en `AGENTS.md`: §10 decía que `verificar.sh` estaba pendiente y §8.3 hablaba del script de reinicio "cuando exista". Le pedí corregirlas:
```
Sí, corrige §10: scripts/verificar.sh ya existe y es la definición de terminado. Indica qué pasos ejecuta y que una tarea solo está terminada si termina con código 0. Es parte de v3, sin fila nueva. Muéstrame cómo quedó §10. No hagas commit.
```
```
Sí, corrige §8.3: scripts/reiniciar_datos_prueba.sh ya existe; es el único script que usa down -v y pide escribir "BORRAR" para confirmar. Revisa si queda alguna otra frase que diga "pendiente" o "cuando exista" sobre algo que ya existe y corrígela también. Muéstrame el resultado de grep -n -i "pendiente\|cuando exista" AGENTS.md. No hagas commit.
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
