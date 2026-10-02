# Prompt 02 — Contexto del proyecto (AGENTS.md v1)

- **Herramienta:** Claude Code 2.1.287 (modo auto)
- **Modelo y versión:** Claude Opus 5.5 (cuenta Claude Pro)
- **Fecha de uso:** 2026-10-02
- **Fase:** Context engineering
- **Commit resultante:** (se completa después del commit)

## Objetivo
Crear un contexto versionado (`AGENTS.md` y `docs/contexto/fases.md`) que permita a cualquier asistente comprender el proyecto, sus reglas, límites de operación y la distinción entre instrucciones y datos no confiables.

## Contexto suministrado
- `docs/contexto/enunciado.md`: requisitos completos.
- `docs/contexto/analisis-excel.md`: hallazgos verificados del Prompt 01, para que las reglas de importación se basen en hechos y no en suposiciones.
- `scripts/analizar_excel.py`: para registrar el único comando real existente.

## Prompt utilizado
```
[PEGAR AQUÍ EL PROMPT 2 COMPLETO]
```

## Extracto de la salida
- `AGENTS.md` (161 líneas) con las 11 secciones solicitadas.
- Decisiones marcadas como PENDIENTE DE DECISIÓN: nombre canónico de SE.12, padre de SE.12.3, tratamiento de filas 42 y 67, representación de valores desconocidos, normalización de códigos, corrección de errores de escritura y política de desactivación con dependencias.
- Comandos: solo el análisis del Excel y la verificación del hash existen; el resto quedó como "pendiente".
- Límites de operación verificables con comandos (`git ls-files`, `sha256sum -c`, `git status`).
- El agente agregó por iniciativa propia un límite: no inventar resultados de pruebas ni evidencias (respaldado por el enunciado, sección 8). Se aceptó.
- `docs/contexto/fases.md` con las 10 fases, documentos entregados y motivo.

Captura: `../evidencias/prompt02-resultado.png`.

## ¿Cumplió el criterio de aceptación?
Sí. Comprobado manualmente con `grep '^## ' AGENTS.md` (11 secciones) y `grep -c "PENDIENTE DE DECISIÓN" AGENTS.md`. La regla de datos no confiables está en la sección 9 y las decisiones pendientes no se presentan como decididas.

## Problemas observados e iteración
- **Problema observado:** ninguno que requiriera revisión del prompt.
- **Prompt revisado:** no fue necesario.
- **Resultado comprobado:** ver comprobación anterior.
