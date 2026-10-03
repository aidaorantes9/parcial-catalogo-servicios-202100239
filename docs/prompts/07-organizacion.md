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
[PEGAR AQUÍ EL PROMPT 7 COMPLETO]
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
