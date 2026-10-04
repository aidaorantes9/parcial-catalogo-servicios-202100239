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
OBJETIVO
Implementar el catálogo de servicios: catálogos de clase, criticidad y tipo, servicios de nivel 1 y nivel 2, búsqueda, filtros, ficha y asignación de responsables.

CONTEXTO
Lee AGENTS.md (ya cargado), docs/contexto/modelo-datos.md (catálogos, servicios, trazabilidad, decisiones D1, D6, D7, D8 y D9), docs/contexto/seguridad.md y la sección 3.3 de docs/contexto/enunciado.md. Reutiliza los permisos, las vistas base y las plantillas existentes. Todavía NO implementes el importador; solo crea los modelos de trazabilidad que el modelo de datos define, para que el importador los use después.

INSTRUCCIONES
1. Modelos y migraciones de ClaseServicio, Criticidad, TipoServicio, el mapeo de correcciones de etiquetas, ServicioNivel1, ServicioNivel2 y las tablas de trazabilidad de importación, exactamente como dice modelo-datos.md (incluye el CHECK minimo <= maximo cuando ambos existen, activo_excel como texto original y estado_revision). Cómo se alimentan los catálogos debe seguir lo que dice modelo-datos.md.
2. Mantenimiento (ADMIN escribe, CONSULTA solo lee) de los tres catálogos, de nivel 1 y de nivel 2, con desactivación y reactivación lógica. Formularios con selects controlados que solo ofrecen opciones activas.
3. Validaciones en servidor con mensajes comprensibles:
   - Obligatorios, código único en su entidad, referencias existentes y activas.
   - mínimo <= máximo cuando ambos existen, en el formulario Y en la base.
   - Un campo vacío se guarda como NULL, nunca como 0 ni como cadena vacía con significado.
   - D9: el usuario responsable debe pertenecer a la sección responsable (con la función de servicio común), no se puede asignar usuario sin sección, y no se puede cambiar el puesto de un usuario a otra sección mientras sea responsable de algún servicio.
   - Solo se pueden asignar secciones y usuarios activos.
   - Extiende D1: una sección no se puede desactivar si es responsable de servicios activos; un nivel 1 no se puede desactivar con servicios de nivel 2 activos. Para la desactivación de un usuario que es responsable, aplica una regla coherente con D1 y D9, impleméntala y explícala.
4. Listado de nivel 2 con búsqueda por código y nombre, filtros por nivel 1, estado del registro (activo), ACTIVO del Excel (S / N / Desconocido / Otros / Todos), clase, criticidad, tipo, estado de revisión y sección responsable, combinables entre sí, y paginación que conserve los filtros. Los campos sin dato deben poder filtrarse como "Sin dato".
5. Ficha del servicio de nivel 2 con todos sus atributos, su nivel 1 (con enlace), responsables, estado de revisión, valores originales y observaciones de importación si existen. Los valores NULL se muestran como "Sin dato" o "Desconocido", nunca como 0. La ficha del nivel 1 lista sus servicios de nivel 2.
6. Agrega el catálogo al menú y conteos al inicio.
7. Pruebas en tests/ con marcadores y docstring con el ID, usando datos de prueba controlados creados en la propia prueba (no dependas del Excel):
   - P05 (catálogo): código duplicado y referencia inexistente o inactiva rechazados con mensaje.
   - P09: crear y editar con mínimo > máximo rechazado en el formulario, y la restricción de la base también lo impide; mínimo = máximo y valores vacíos sí se permiten y quedan NULL.
   - P10: búsqueda por código y por nombre, cada filtro por separado y combinados, devuelven exactamente los registros esperados; la paginación conserva los filtros.
   - P11: asignar un usuario de otra sección es rechazado; asignar usuario sin sección es rechazado; cambiar el puesto de un responsable a otra sección es rechazado.
   - Extensiones de D1 y la regla de desactivación de usuarios responsables.
   - Extiende P03: CONSULTA lee listados y fichas del catálogo y recibe 403 en todas las escrituras.
8. Actualiza modelo-datos.md con lo que hayas tenido que concretar y AGENTS.md (§7 si hay comandos nuevos), sin fila nueva en el registro de cambios.

RESTRICCIONES
- No implementes el importador ni leas el Excel en esta fase.
- No inventes valores para campos ausentes.
- No uses `down -v`. No hagas commit.

SALIDA ESPERADA
Modelos, migraciones, vistas, formularios, plantillas, pruebas, documentación actualizada y la salida real de `bash scripts/verificar.sh`.

CRITERIO DE ACEPTACIÓN
`bash scripts/verificar.sh` termina con código 0 con P03, P05, P09, P10 y P11 en verde, y todas las pruebas anteriores siguen pasando.
```

## Seguimiento por corte de conexión
La computadora se suspendió cuando el asistente ya tenía el código y las pruebas en verde y estaba actualizando la documentación, y la sesión dio "API Error: The response stopped arriving". Revisé que la red de la VM funcionara y, sin limpiar la sesión, le pedí:
```
La conexión se cortó mientras actualizabas la documentación. Revisa con git status y git diff qué alcanzaste a cambiar en modelo-datos.md, AGENTS.md y seguridad.md, completa lo que falte del punto 8 de la tarea y luego ejecuta bash scripts/verificar.sh. Al final dame el resumen completo de la tarea (qué se hizo, decisiones que debo revisar, incluida la regla de desactivación de usuarios responsables, y la salida real de la verificación). No hagas commit.
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
