# Prompt 07: Estructura organizacional

- Herramienta: Claude Code 2.1.288 (modo auto)
- Modelo: Claude Opus 5.5 (cuenta Claude Pro)
- Fecha de uso: 2026-10-02
- Fase: Organización
- Commit resultante: `1da55ac`

## Objetivo
Implementar el mantenimiento de Empresa, Área, Departamento, Sección y Puesto con baja lógica, validaciones en el servidor y la política D1 para registros con dependientes.

## Contexto suministrado
Limpié la sesión con `/clear`. Le indiqué leer `modelo-datos.md` (organización, D1 y supuestos), `seguridad.md` y la sección 3.2 del enunciado, y reutilizar los permisos y plantillas que ya existían.

## Prompt utilizado
```
OBJETIVO
Implementar el mantenimiento de Empresa, Área, Departamento, Sección y Puesto (los modelos ya existen).

CONTEXTO
Lee AGENTS.md (ya cargado), docs/contexto/modelo-datos.md (organización, decisión D1 y supuestos), docs/contexto/seguridad.md y la sección 3.2 de docs/contexto/enunciado.md. Reutiliza los mixins de cuentas/permisos.py y la plantilla base existente.

INSTRUCCIONES
1. Para cada entidad: listado paginado con búsqueda por código y nombre y filtro por estado y por padre; detalle que muestre el padre, la ruta completa hasta la empresa y los hijos directos; crear, editar, desactivar y reactivar (baja lógica). Usa vistas genéricas o una base común para no repetir código.
2. Permisos: ADMIN puede todo. CONSULTA puede ver listados y detalles (lectura de datos funcionales) pero recibe 403 en cualquier escritura, aunque haga la petición directa.
3. Validaciones en servidor con mensajes comprensibles en español:
   - Código duplicado dentro del mismo padre (y en Empresa, duplicado global), sin distinguir mayúsculas si así está en el modelo.
   - Padre inexistente o inactivo al crear o al cambiar de padre.
   - Aplica la decisión D1: no se puede desactivar un registro con dependientes activos (incluye usuarios activos en un puesto); se muestra la lista de dependientes que lo impiden.
   - No se puede reactivar un registro si su padre está inactivo.
   - Nunca DELETE físico desde la interfaz.
4. En el detalle del Puesto, muestra sus usuarios. En el detalle y la lista de usuarios, muestra la empresa derivada (puesto → sección → departamento → área → empresa) sin guardarla.
5. Agrega las entradas al menú y una página de inicio con conteos básicos (empresas, áreas, departamentos, secciones, puestos y usuarios activos).
6. Pruebas en tests/ con marcadores p04 y p05 y docstring con el ID:
   - P04: crear una jerarquía completa a través de las vistas (POST como ADMIN), crear un usuario en el puesto y comprobar que se recupera toda la ruta y la empresa derivada.
   - P05 (organización): código duplicado dentro del mismo padre rechazado con mensaje; el mismo código en otro padre sí se permite; padre inexistente y padre inactivo rechazados con mensaje.
   - Política D1: desactivar con dependientes activos se rechaza y lista los dependientes; sin dependientes activos se permite; reactivar con padre inactivo se rechaza.
   - Extiende P03: CONSULTA puede hacer GET de listados y detalles de organización y recibe 403 en crear, editar, desactivar y reactivar.
7. Documenta brevemente en docs/contexto/modelo-datos.md (sección de D1) cómo quedó implementada la política. No agregues fila al registro de cambios de AGENTS.md.

RESTRICCIONES
- No cambies la lógica de autenticación existente salvo que sea necesario, y explícalo si lo haces.
- Interfaz simple, coherente con las plantillas existentes.
- No uses `down -v`. No hagas commit.

SALIDA ESPERADA
Vistas, formularios, plantillas, URLs, pruebas y la salida real de `bash scripts/verificar.sh`.

CRITERIO DE ACEPTACIÓN
`bash scripts/verificar.sh` termina con código 0 con P03, P04 y P05 en verde.
```

## Extracto de la salida
- Un solo juego de vistas para las cinco entidades: listado con búsqueda, filtros y paginación; detalle con la ruta hasta la empresa y los hijos; crear, editar, desactivar y reactivar.
- Desactivar y reactivar solo por POST. Ninguna vista acepta DELETE.
- El selector de padre solo ofrece padres activos, y el mensaje distingue un padre inexistente de uno inactivo.
- Política D1: si hay dependientes activos no se guarda nada y se muestra la lista con enlaces. Tampoco se puede reactivar si el padre está inactivo.
- Nuevo `LecturaRequeridaMixin` para que CONSULTA pueda leer. La autenticación no cambió.
- La lista de usuarios muestra la empresa derivada del puesto.

Decisiones del asistente que revisé y acepté:
- Los códigos distinguen mayúsculas (`EMP` y `emp` son distintos), según el supuesto S1.
- Se puede editar un registro con padre inactivo si no se cambia de padre, porque el enunciado solo prohíbe asociaciones nuevas.
- CONSULTA ve los usuarios de un puesto, pero sin enlace a su ficha.

Captura: `../evidencias/prompt07-resultado.png`.

## ¿Cumplió el criterio de aceptación?
Sí. `bash scripts/verificar.sh` terminó con código 0 y 63 pruebas aprobadas, incluidas P03, P04 y P05 (log `docs/evidencias/verificacion-20261002-1945.log`).

También lo probé en el navegador:
- Como admin creé la empresa EMP1 y el área AR1; el detalle muestra la ruta completa (`../evidencias/prompt07-jerarquia.png`).
- Intenté desactivar EMP1 con AR1 activa y se rechazó mostrando el dependiente (`../evidencias/prompt07-d1-rechazo.png`).
- Como consulta vi la lista de empresas sin botones de escritura (`../evidencias/prompt07-consulta-lectura.png`).

Los datos de EMP1 y AR1 quedaron en la base de evaluación a propósito, para usarlos después en la prueba de persistencia.

## Problemas observados e iteración
No hizo falta revisar el prompt.
