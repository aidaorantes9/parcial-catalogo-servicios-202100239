# Prompt 04 — Decisiones del modelo y actualización de contexto v2

- **Herramienta:** Claude Code 2.1.287 (modo auto)
- **Modelo y versión:** Claude Opus 5.5 (cuenta Claude Pro)
- **Fecha de uso:** 2026-10-02
- **Fase:** Context engineering (actualización #1) / Modelo de datos
- **Commit resultante:** `d10c972`

## Objetivo
Registrar las decisiones humanas sobre D1–D9 y actualizar `AGENTS.md` y `modelo-datos.md` (contexto v2), resolviendo las interpretaciones que el asistente señaló.

## Contexto suministrado
- `AGENTS.md` (vía `CLAUDE.md`), `docs/contexto/modelo-datos.md` con las opciones del Prompt 03.

## Motivo de la actualización de contexto
Los hallazgos del análisis del Excel (conflicto SE.12, SE.12.3 sin nivel 1, filas 42 y 67, valores ausentes, errores de escritura) requerían reglas explícitas antes de implementar. Hasta este punto estaban marcadas como PENDIENTE DE DECISIÓN.

## Prompt utilizado (4a — decisiones D1–D9)
```
[PEGAR AQUÍ EL PROMPT DE DECISIONES DEL PASO 21]
```

## Seguimiento 4b — interpretación de ACTIVO
El asistente propuso guardar los valores desconocidos de ACTIVO como NULL. Se corrigió porque el enunciado pide "conservar los valores desconocidos como tales" y con NULL se perdería un valor original distinto de S/N.
```
[PEGAR AQUÍ LA RESPUESTA DEL PASO 22]
```

## Seguimiento 4c — valores fuera de lista en F, G y H
El asistente detectó que no había regla para este caso.
```
[PEGAR AQUÍ LA REGLA F–H]
```

## Extracto de la salida
- `AGENTS.md` v2 (174 líneas): §4 y §5 con las reglas decididas; fila v2 en el registro de cambios.
- `modelo-datos.md`: decisiones D1–D9 con su motivo; nueva observación `POSIBLE_ERROR_ESCRITURA` (Análsis); `VALOR_NO_RECONOCIDO` para E, F, G y H; `activo_excel` como texto original; filtros independientes por ACTIVO del Excel y por baja lógica.
- `fases.md`: fase de modelo marcada como realizada.
- El asistente señaló que para probar la regla F–H se necesitará un Excel de prueba, porque el original no contiene valores fuera de lista.

Capturas: `../evidencias/prompt03-resultado.png`, `../evidencias/prompt04-decisiones.png`, `../evidencias/prompt04-ajuste-activo.png`, `../evidencias/prompt04-regla-fgh.webp`.

## ¿Cumplió el criterio de aceptación?
Sí. `grep -c "PENDIENTE DE DECISIÓN" AGENTS.md docs/contexto/modelo-datos.md` devolvió 0 y 0; AGENTS.md tiene la fila v2; `sha256sum -c` confirma el Excel intacto.

## Decisiones humanas frente a sugerencias de la IA
- Claude Code sugirió dos veces respuestas automáticas ("Acepto todas tus recomendaciones D1–D9" y "De acuerdo, DESCONOCIDO como NULL está bien"). No se usaron.
- Se ajustaron D7 (observar "Análsis") y D8 (filtros separados), y se corrigió la interpretación de ACTIVO desconocido.
