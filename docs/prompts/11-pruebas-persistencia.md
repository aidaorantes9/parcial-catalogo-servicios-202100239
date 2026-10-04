# Prompt 11: Pruebas P01 a P12, persistencia y matriz

- Herramienta: Claude Code 2.1.288 (modo auto)
- Modelo: Claude Opus 5.5 (cuenta Claude Pro)
- Fecha de uso: 2026-10-03
- Fase: Pruebas
- Commit resultante: `4503f11`

## Objetivo
Completar la automatización de los escenarios P01 a P12, crear la prueba de persistencia P12 y documentar la matriz de pruebas.

## Contexto suministrado
Limpié la sesión con `/clear`. Le indiqué leer la sección 6 del enunciado y revisar `tests/`, `src/pytest.ini` y `scripts/`.

## Prompt utilizado
```
OBJETIVO
Completar la automatización de los escenarios P01 a P12, agregar la prueba de persistencia P12 y documentar la matriz de pruebas.

CONTEXTO
Lee AGENTS.md (ya cargado), la sección 6 de docs/contexto/enunciado.md y revisa tests/, src/pytest.ini y scripts/.

INSTRUCCIONES
1. Revisa que cada escenario P01 a P11 tenga al menos una prueba con su marcador (p01 … p11) y un docstring con su ID. Si falta algún marcador o hay pruebas sin marcar que pertenecen a un escenario, corrígelo sin cambiar lo que prueban.
2. Crea scripts/prueba_persistencia.sh (P12), que trabaje sobre la base de evaluación sin borrar nada:
   a. Exige que los servicios estén levantados y que el catálogo esté importado; si no, falla con mensaje claro.
   b. Registra el estado antes: conteo de servicios de nivel 1 y 2, usuarios, empresas, asignaciones y ejecuciones de importación.
   c. Crea un registro marcador con un código único que incluya la fecha y hora (por ejemplo una empresa P12-AAAAMMDDHHMM marcada como dato de prueba).
   d. Ejecuta `docker compose down` (SIN -v) y luego `docker compose up -d --wait`.
   e. Verifica que el marcador existe y que los conteos son iguales a los de antes (más el marcador). Después desactiva el marcador (baja lógica).
   f. Imprime PASA o FALLA por cada comprobación, sale con código 0 si todo pasa y 1 si algo falla, y guarda la salida en docs/evidencias/persistencia-AAAAMMDD-HHMM.log (con sufijo si ya existe).
3. Agrega a scripts/verificar.sh la opción --completo, que además de todo lo actual ejecute prueba_persistencia.sh al final. Sin la opción, verificar.sh se comporta igual que ahora.
4. Agrega a scripts/pruebas.sh la posibilidad de correr un escenario con su marcador (ejemplo: bash scripts/pruebas.sh -m p06) y documéntalo.
5. Crea docs/contexto/matriz-pruebas.md con una tabla: ID, escenario, resultado esperado, tipo (unitaria, integración o extremo a extremo), archivos y funciones de prueba, comando para ejecutarlo solo. Explica brevemente qué significa cada tipo en este proyecto, cómo se aíslan los datos (base test_* de pytest-django frente a la base de evaluación que usa P12) y qué casos extra existen además de P01–P12 (D1, D9, ciclo de harness, referencias inactivas, etc.).
6. Actualiza AGENTS.md: mapa de documentos y §7 con los comandos nuevos, sin fila nueva en el registro de cambios. Corrige las líneas que dicen que P12 está pendiente.
7. Ejecuta y muéstrame la salida real de:
   - bash scripts/pruebas.sh -m p06
   - bash scripts/verificar.sh --completo

RESTRICCIONES
- No uses `down -v` ni borres volúmenes. P12 solo hace `down` y `up`.
- No borres datos de la base de evaluación; el marcador queda dado de baja, no eliminado.
- No hagas commit.

SALIDA ESPERADA
Scripts, marcadores corregidos, matriz de pruebas, AGENTS.md actualizado y las salidas reales.

CRITERIO DE ACEPTACIÓN
`bash scripts/verificar.sh --completo` termina con código 0, incluida la persistencia, y cada escenario P01–P12 aparece en la matriz con su prueba y su comando.
```

## Seguimiento
`fases.md` seguía marcando la fase de pruebas como prevista, así que le pedí:
```
Actualiza docs/contexto/fases.md marcando la fase 9 (pruebas) como realizada, con los documentos usados y el resultado. Solo eso. No hagas commit.
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
