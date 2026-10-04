# Prompt 11: Pruebas P01 a P12, persistencia y matriz

- Herramienta: Claude Code 2.1.288 (modo auto)
- Modelo: Claude Opus 5.5 (cuenta Claude Pro)
- Fecha de uso: 2026-10-03
- Fase: Pruebas
- Commit resultante: (se completa después del commit)

## Objetivo
Completar la automatización de los escenarios P01 a P12, crear la prueba de persistencia P12 y documentar la matriz de pruebas.

## Contexto suministrado
Limpié la sesión con `/clear`. Le indiqué leer la sección 6 del enunciado y revisar `tests/`, `src/pytest.ini` y `scripts/`.

## Prompt utilizado
```
[PEGAR AQUÍ EL PROMPT 11 COMPLETO]
```

## Seguimiento
`fases.md` seguía marcando la fase de pruebas como prevista, así que le pedí:
```
[PEGAR AQUÍ EL MENSAJE DE FASES.MD]
```

## Extracto de la salida
- P01 a P11 ya tenían marcador. Agregó el ID que faltaba en el docstring de 8 pruebas y reclasificó tres, sin cambiar ninguna aserción.
- `scripts/prueba_persistencia.sh` nuevo para P12: registra los conteos, crea una empresa marcador, hace `docker compose down` sin `-v` y `up --wait`, comprueba que todo sigue igual y da de baja el marcador.
- `verificar.sh --completo` ejecuta además la persistencia, y `pruebas.sh -m pNN` corre un escenario solo.
- `docs/contexto/matriz-pruebas.md` con los 12 escenarios, el tipo de cada prueba, sus funciones, el comando y cómo se aíslan los datos.
- El primer intento falló en `ruff check` porque cinco líneas pasaron de 100 columnas al agregar los IDs. El asistente las corrigió y volvió a ejecutar.
- Antes de terminar ejecutó `verificar.sh` por su cuenta, porque `AGENTS.md` §10 lo exige. Lo tomé como señal de que el contexto sí está guiando al asistente.

El asistente aclaró que no hay pruebas con un navegador real: P12 es la única de extremo a extremo y P01 a P11 son de integración. La revisión de la interfaz la hice yo a mano en Firefox en cada fase (capturas de los prompts 06 a 09).

Captura: `../evidencias/prompt11-resultado.png`.

## ¿Cumplió el criterio de aceptación?
Sí. Ejecuté yo misma `bash scripts/verificar.sh --completo` y terminó con código 0. P12 comprobó que el volumen de PostgreSQL era el mismo, que el marcador existía después del reinicio y que los conteos no cambiaron (46 servicios, 4 usuarios, 4 asignaciones y 4 ejecuciones). Captura: `../evidencias/prompt11-persistencia.png`.

El conteo de nivel 1 sale 13 porque incluye el servicio de prueba T1 que creé en la fase del catálogo (está dado de baja). Los importados son 12.

## Problemas observados e iteración
No hizo falta revisar el prompt.
