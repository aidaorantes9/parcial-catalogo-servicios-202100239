# Prompt 04: Decisiones del modelo y actualización de contexto v2

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

## Prompt utilizado (4a: decisiones D1–D9)
```
OBJETIVO
Registrar mis decisiones sobre el modelo de datos y actualizar el contexto del proyecto (actualización de contexto v2).

DECISIONES DEL USUARIO (revisadas una por una; no son una aceptación automática)
- D1: Acepto. Se rechaza desactivar un registro con dependientes activos y se muestra la lista de dependientes. Motivo: evita registros huérfanos o asociados a padres inactivos sin borrar ni cambiar información en silencio.
- D2: Acepto. Las filas 42 y 67 no crean servicios: se cuentan como omitidas y se registra una observación con sus valores E–H. Motivo: el enunciado prohíbe asignarlas automáticamente a otro servicio.
- D3: Acepto. Nombre canónico de SE.12: "Suministrar Analitica" (B99), se conservan ambos nombres como evidencia, observación de conflicto y estado PENDIENTE_REVISION. Motivo: es la primera fila del grupo, como en los otros 11 grupos, abarca a los tres hijos y B100 es idéntico al nombre del hijo SE.12.3, lo que sugiere un error de copiado.
- D4: Acepto. SE.12.3 se asigna a SE.12 por prefijo de código, con observación y PENDIENTE_REVISION.
- D5: Acepto. No se normalizan SE.12.1, SE.12.2 y SE.12.3; se registra observación de formato.
- D6: Acepto. Ausencias se guardan como NULL con estado_revision = PENDIENTE_REVISION; nunca 0 ni valores inventados.
- D7: Acepto con ajuste. Solo se corrige "Demostration" → "Demonstration" en etiqueta_mostrada, registrado en el mapeo. AJUSTE: "Análsis" (D100) no se corrige, pero se registra una observación de posible error de escritura.
- D8: Acepto con ajuste. activo_excel (S, N o DESCONOCIDO) y activo (baja lógica) son campos independientes; todo lo importado entra con activo = true. AJUSTE: el listado de servicios debe permitir filtrar por ambos campos por separado, para que servicios como SE.05.01 (ACTIVO = N) sean localizables.
- D9: Acepto. Validación en servidor con clean() y una función de servicio común, y se rechaza cambiar el puesto de un usuario responsable a otra sección mientras siga asignado.
- S4, S6 y S7: Acepto los tres supuestos.

INSTRUCCIONES
1. Actualiza docs/contexto/modelo-datos.md: reemplaza cada "PENDIENTE DE DECISIÓN DEL USUARIO" por la decisión tomada y su motivo, e incorpora los dos ajustes (D7 y D8) donde correspondan (diccionario, observaciones, filtros).
2. Actualiza AGENTS.md: en §4 y §5 reemplaza los "PENDIENTE DE DECISIÓN" por las decisiones finales, en forma de reglas breves. Agrega docs/contexto/modelo-datos.md al mapa de documentos si no está.
3. Agrega en el registro de cambios de contexto de AGENTS.md la fila: "v2 – 2026-10-02 – decisiones de modelo D1–D9 – los hallazgos del análisis del Excel (conflicto SE.12, SE.12.3 sin nivel 1, filas 42 y 67, valores ausentes, errores de escritura) requerían reglas explícitas antes de implementar".
4. Actualiza docs/contexto/fases.md marcando "Modelo de datos" como realizada.

RESTRICCIONES
- No cambies otras secciones ni crees código.
- AGENTS.md debe seguir por debajo de ~250 líneas.
- No hagas commit.

SALIDA ESPERADA
Los tres archivos actualizados y un resumen de qué cambió en cada uno.

CRITERIO DE ACEPTACIÓN
`grep -c "PENDIENTE DE DECISIÓN" AGENTS.md docs/contexto/modelo-datos.md` devuelve 0 en ambos archivos y AGENTS.md tiene la fila v2 en su registro de cambios.
```

## Seguimiento 4b: interpretación de ACTIVO
El asistente propuso guardar los valores desconocidos de ACTIVO como NULL. Se corrigió porque el enunciado pide "conservar los valores desconocidos como tales" y con NULL se perdería un valor original distinto de S/N.
```
Respuesta a tus interpretaciones:

1. D8/D6: Ajuste. activo_excel debe conservar el valor original del Excel como texto: "S" y "N" se reconocen; cualquier otro valor no vacío se guarda tal cual y genera una observación VALOR_NO_RECONOCIDO; solo la celda vacía se guarda como NULL. La interfaz muestra NULL como "Desconocido" y el filtro ofrece S / N / Desconocido / Otros / Todos. Motivo: el enunciado pide "conservar los valores desconocidos como tales", y con NULL se perdería un valor original distinto de S/N.

2. D7: Correcto. "Analitica", "Area 8" y "Area 9" se conservan sin corrección ni observación porque son valores originales; solo se observa "Análsis".

Actualiza docs/contexto/modelo-datos.md y AGENTS.md con el punto 1 (sin agregar una nueva versión al registro de cambios: forma parte de v2). No hagas commit. Al terminar, ejecuta y muéstrame:
grep -c "PENDIENTE DE DECISIÓN" AGENTS.md docs/contexto/modelo-datos.md
wc -l AGENTS.md
sha256sum -c data/CatalogoServicios.xlsx.sha256
```

## Seguimiento 4c: valores fuera de lista en F, G y H
El asistente detectó que no había regla para este caso.
```
Regla para valores fuera de lista en F, G y H (clase, criticidad, tipo):
- No se crean entradas nuevas en los catálogos automáticamente.
- La FK correspondiente queda en NULL, el servicio queda con estado_revision = PENDIENTE_REVISION y se registra una observación VALOR_NO_RECONOCIDO con columna, fila y valor.
- El valor original se conserva en los valores originales (JSONB) de la tabla de origen del servicio, y la ficha del servicio lo muestra junto a la observación.
- La comparación con el catálogo es exacta contra etiqueta_original (sin recortar espacios ni cambiar mayúsculas), igual que en activo_excel.
Motivo: los catálogos son opciones controladas según el enunciado; crear valores en silencio los contaminaría, y descartar el valor perdería el dato original.

Actualiza modelo-datos.md y AGENTS.md (§5) con esta regla, como parte de v2 (sin nueva fila en el registro). No hagas commit. Al terminar ejecuta y muéstrame:
grep -c "PENDIENTE DE DECISIÓN" AGENTS.md docs/contexto/modelo-datos.md
wc -l AGENTS.md
git status --short
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
