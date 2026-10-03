# Prompt 03: Diseño del modelo de datos

- **Herramienta:** Claude Code 2.1.287 (modo auto)
- **Modelo y versión:** Claude Opus 5.5 (cuenta Claude Pro)
- **Fecha de uso:** 2026-10-02
- **Fase:** Modelo de datos
- **Commit resultante:** `6f07d36`

## Objetivo
Diseñar el modelo de datos completo (ER, diccionario, mapeo Excel → BD) antes de escribir código, y obtener opciones fundamentadas para cada decisión pendiente sin que el asistente las tome por su cuenta.

## Contexto suministrado
- `AGENTS.md` (cargado automáticamente vía `CLAUDE.md`): reglas, límites y decisiones pendientes.
- `docs/contexto/enunciado.md` (secciones 2, 3 y 3.4): requisitos del modelo e importación.
- `docs/contexto/analisis-excel.md`: hechos verificados del Excel.

## Prompt utilizado
```
[PEGAR AQUÍ EL PROMPT 3 COMPLETO]
```

## Extracto de la salida
- `docs/contexto/modelo-datos.md`: diagrama ER en Mermaid con 17 tablas, diccionario de datos, mapeo de columnas A–L, tabla restricción → implementación → prueba.
- Campos agregados por diseño y justificados: `orden`, `fila_origen`, `sin_cambios`, `severidad`, `creado_en`, `actualizado_en`.
- Clave natural para idempotencia: código (nivel 1), `codigo_original` (nivel 2), `etiqueta_original` (catálogos).
- 9 decisiones pendientes (D1–D9) con opciones, ventajas, desventajas y recomendación, y 3 supuestos a revisar (S4, S6, S7).
- El asistente verificó el hash del Excel y que solo se creó el archivo pedido.

Captura: `../evidencias/prompt03-resultado.png`.

## ¿Cumplió el criterio de aceptación?
Sí. Las 12 columnas están mapeadas, cada restricción tiene implementación indicada y ninguna decisión fue tomada por el asistente.

## Problemas observados e iteración
- **Problema observado:** al terminar, Claude Code sugirió automáticamente la respuesta "Acepto todas tus recomendaciones D1–D9". No se usó: las decisiones se revisaron una por una y se ajustaron D7 (registrar observación para "Análsis") y D8 (filtrar por ACTIVO del Excel y por baja lógica). Ver Prompt 04.
- **Prompt revisado:** no fue necesario.
- **Resultado comprobado:**
