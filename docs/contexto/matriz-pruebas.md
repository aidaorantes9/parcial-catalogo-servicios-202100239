# Matriz de pruebas P01–P12

Escenarios de la sección 6 del enunciado (`docs/contexto/enunciado.md`), qué los automatiza y cómo se ejecuta
cada uno por separado. Todas las rutas de prueba son relativas a la raíz del repositorio; `tests/` se monta en
el contenedor `web` en `/app/tests` (solo lectura).

## 1. Tipos de prueba en este proyecto

| Tipo | Qué significa aquí | Con qué se ejecuta |
|---|---|---|
| **Unitaria** | Una regla aislada sin pasar por HTTP: `full_clean()`/`clean()` de un modelo, una restricción de PostgreSQL (`CheckConstraint`, `UniqueConstraint`), las funciones de servicio comunes de `catalogo/servicios.py` (`asignar_responsables`, D9) o el hasher de contraseñas. Usa la base `test_*` porque las reglas viven en el modelo y en la base. | pytest + pytest-django dentro de `web` |
| **Integración** | Recorre varias capas juntas: cliente de pruebas de Django → URL → vista → permisos → formulario → modelo → PostgreSQL, o un comando de gestión (`importar_catalogo`, `cargar_demo`, `crear_cuentas_demo`) con el Excel real de `data/` (solo lectura) y se revisa el resultado en la base y en las pantallas. | pytest + pytest-django dentro de `web` |
| **Extremo a extremo** | La pila completa de Docker Compose (`db` + `web` + volumen `datos_postgres`) con la base de evaluación real, manipulada desde fuera como lo haría un operador: se reinician los contenedores y se comprueba lo que queda. | `scripts/prueba_persistencia.sh` (P12) |

No hay pruebas automáticas en un navegador real (Selenium/Playwright): la interfaz se revisa manualmente en
la evaluación; las pruebas de integración sí recorren las vistas y comprueban el HTML devuelto.

## 2. Matriz

Comando general por escenario: `bash scripts/pruebas.sh -m pNN`. Una sola función:
`bash scripts/pruebas.sh "tests/ARCHIVO.py::FUNCION"`.

| ID | Escenario | Resultado esperado | Tipo | Archivos y funciones de prueba | Comando |
|---|---|---|---|---|---|
| P01 | Inicio de sesión válido e inválido | Acceso correcto y rechazo de credenciales incorrectas | Integración (+ unitaria del hash) | `tests/test_p01_login.py`: `test_login_valido_con_usuario_o_correo` (usuario o correo, sin distinguir mayúsculas), `test_login_invalido_rechazado_con_mensaje_generico`, `test_password_guardada_con_argon2` (unitaria) | `bash scripts/pruebas.sh -m p01` |
| P02 | Acceso sin sesión, cierre de sesión y usuario inactivo | Operaciones protegidas rechazadas en los tres casos | Integración | `tests/test_p02_sesion.py`: `test_sin_sesion_se_rechazan_paginas_y_operaciones`, `test_login_y_salud_no_requieren_sesion`, `test_logout_invalida_la_sesion_en_el_servidor`, `test_logout_solo_por_post`, `test_logout_exige_token_csrf`, `test_usuario_inactivo_no_puede_iniciar_sesion`, `test_sesion_abierta_de_usuario_desactivado_se_invalida`, `test_cambio_de_password_invalida_sesiones_del_usuario` | `bash scripts/pruebas.sh -m p02` |
| P03 | Usuario de consulta intenta modificar datos | Rechazo en el servidor; lectura permitida | Integración | `tests/test_p03_roles.py` (403 en escritura, no escala su rol, no ve hashes), `tests/test_p03_organizacion.py` y `tests/test_p03_catalogo.py` (lectura permitida, 403 en toda escritura, reactivar no cambia nada), `tests/test_importacion_pantalla.py::test_consulta_y_anonimo_no_acceden`, `tests/test_usuarios_admin.py` (mantenimiento de usuarios solo ADMIN: alta con hash, contraseña débil, puesto inactivo, edición, auto-baja impedida, solo POST, listado) | `bash scripts/pruebas.sh -m p03` |
| P04 | Crear una jerarquía y asignar un usuario | Relaciones válidas y recuperables | Integración | `tests/test_p04_jerarquia.py`: `test_jerarquia_completa_y_usuario_desde_las_vistas` (Empresa → … → Puesto por POST, usuario en el puesto, ruta y empresa derivada), `test_listado_busqueda_filtros_y_paginacion` | `bash scripts/pruebas.sh -m p04` |
| P05 | Código duplicado o referencia inexistente | Rechazo con mensaje comprensible | Integración (+ unitaria de modelo) | `tests/test_p05_organizacion.py` (duplicado en el mismo padre y en cada nivel, mismo código en otro padre permitido, padre inexistente o inactivo), `tests/test_p05_catalogo.py` (código N1/N2/catálogo duplicado, referencia inexistente o inactiva, obligatorios; `test_modelo_rechaza_nivel1_inactivo_fuera_del_formulario` es unitaria), `tests/test_d1_organizacion.py` y `tests/test_d1_catalogo.py` (desactivación con dependientes, ver §4) | `bash scripts/pruebas.sh -m p05` |
| P06 | Importar el archivo original | 12 códigos de nivel 1 y 46 servicios de nivel 2; incidencias registradas | Integración | `tests/test_p06_importacion.py`: `test_p06_importar_original_produce_12_n1_y_46_n2`, `test_p06_incidencias_registradas`, `test_p06_filas_de_continuacion_y_filas_42_67_no_crean_servicios`, `test_p06_trazabilidad_en_la_ficha`, `test_original_con_hash_alterado_aborta` | `bash scripts/pruebas.sh -m p06` |
| P07 | Repetir la importación | Ningún duplicado; resultado trazable | Integración | `tests/test_p07_reimportacion.py`: `test_p07_segunda_importacion_sin_duplicados`, `test_p07_la_ficha_sigue_mostrando_las_observaciones`, `test_p07_reimportacion_respeta_ediciones_manuales`, `test_p07_reimportacion_no_borra_asignaciones_de_cargar_demo`; `tests/test_importacion_pantalla.py::test_admin_ve_historial_y_observaciones`; `tests/test_referencia_inactiva.py` (ver §4) | `bash scripts/pruebas.sh -m p07` |
| P08 | Revisar SE.12 y atributos ausentes | Política de conflicto aplicada y ausencias conservadas | Integración | `tests/test_p08_se12_ausencias.py`: `test_p08_se12_nombre_canonico_y_evidencia` (D3), `test_p08_filas_99_a_101_con_null_y_pendiente_revision` (D4–D6), `test_p08_activo_excel_conserva_el_texto_original` (D8), `test_p08_valores_fuera_de_lista_y_activo_no_reconocido` (Excel modificado en un directorio temporal) | `bash scripts/pruebas.sh -m p08` |
| P09 | Crear o editar servicio con mínimo mayor que máximo | Validación impide guardar | Integración (+ unitaria de la restricción) | `tests/test_p09_minimo_maximo.py`: `test_crear_con_minimo_mayor_que_maximo_se_rechaza`, `test_editar_con_minimo_mayor_que_maximo_se_rechaza`, `test_restriccion_de_la_base_impide_minimo_mayor_que_maximo` (unitaria), `test_minimo_igual_a_maximo_y_un_solo_extremo_se_permiten`, `test_campos_vacios_quedan_null_y_cero_se_conserva`, `test_ficha_muestra_sin_dato_y_desconocido_nunca_cero`, `test_editar_conserva_valor_original_no_reconocido_y_espacios` | `bash scripts/pruebas.sh -m p09` |
| P10 | Buscar y filtrar servicios | Resultados coherentes con los criterios | Integración | `tests/test_p10_busqueda.py`: `test_sin_filtros_muestra_solo_registros_activos`, `test_busqueda_por_codigo_y_por_nombre`, `test_cada_filtro_por_separado`, `test_filtros_combinados`, `test_valores_de_filtro_invalidos_se_ignoran`, `test_paginacion_conserva_los_filtros` | `bash scripts/pruebas.sh -m p10` |
| P11 | Asignar responsable de una sección distinta | Operación rechazada | Integración (+ unitaria D9) | `tests/test_p11_responsable.py`: `test_usuario_de_otra_seccion_se_rechaza_en_el_formulario`, `test_usuario_sin_seccion_se_rechaza`, `test_funcion_de_servicio_comun_valida_la_seccion` (unitaria, D9), `test_asignacion_valida_se_guarda_y_se_ve_en_la_ficha`, `test_solo_secciones_y_usuarios_activos`, `test_cambiar_puesto_de_responsable_a_otra_seccion_se_rechaza`, `test_cambio_de_puesto_se_valida_en_el_modelo` (unitaria), `test_mover_puesto_de_un_responsable_a_otra_seccion_se_rechaza` | `bash scripts/pruebas.sh -m p11` |
| P12 | Reiniciar contenedores sin eliminar volúmenes | Persisten los datos previamente registrados | Extremo a extremo | `scripts/prueba_persistencia.sh`: exige `db`/`web` healthy y catálogo importado; registra conteos (N1, N2, usuarios, empresas, asignaciones, ejecuciones); crea la empresa marcador `P12-AAAAMMDDHHMMSS`; `docker compose down` (sin `-v`) y `up -d --wait`; comprueba volumen, marcador y conteos; da de baja el marcador. Log: `docs/evidencias/persistencia-AAAAMMDD-HHMM.log` | `bash scripts/prueba_persistencia.sh` (equivalentes: `bash scripts/pruebas.sh -m p12`, `bash scripts/verificar.sh --completo`) |

Varios escenarios a la vez: `bash scripts/pruebas.sh -m "p06 or p07 or p08"`. Todas las pruebas de pytest:
`bash scripts/pruebas.sh`. Verificación completa con P12: `bash scripts/verificar.sh --completo`.

## 3. Aislamiento de datos

- **Pruebas de pytest (P01–P11 y casos extra)**: pytest-django crea una base aparte, `test_<POSTGRES_DB>`
  (`DATABASES["default"]["TEST"]["NAME"]` en `src/config/settings.py`), en el mismo servidor PostgreSQL. Cada
  prueba corre dentro de una transacción que se revierte al terminar, y la base `test_*` se destruye al final
  de la sesión. `tests/test_humo.py::test_pruebas_usan_base_de_pruebas` falla si la conexión no apunta a
  `test_*`. Los datos se crean en la propia prueba (fixtures de `tests/conftest.py`) o importando el Excel
  original, que está montado en solo lectura; los Excel modificados se generan en `tmp_path` y el original
  nunca se guarda. Nada de esto toca la base de evaluación.
- **P12**: por definición necesita la base de evaluación real y su volumen, así que no puede usar `test_*`.
  Para no destruir información solo **agrega** un registro identificable (empresa `P12-…` con el nombre
  «Dato de prueba P12 (persistencia) — no usar»), nunca borra: al final la da de baja (`activo = false`) y el
  registro queda como evidencia. Usa `docker compose down` **sin** `-v` y comprueba que el volumen
  `datos_postgres` es el mismo (mismo nombre y fecha de creación). Cada ejecución deja una empresa inactiva
  más; son filas de prueba distinguibles por su código.
- El único script que borra datos es `scripts/reiniciar_datos_prueba.sh` (pide escribir `BORRAR`); ninguna
  prueba lo usa.

## 4. Casos extra (además de P01–P12)

| Caso | Qué comprueba | Pruebas | Marcador / comando |
|---|---|---|---|
| D1: desactivación con dependientes | Desactivar con hijos, usuarios, servicios o valores de catálogo activos se rechaza y lista los dependientes; sin cascada; reactivar bajo padre inactivo se rechaza; GET no cambia estado | `tests/test_d1_organizacion.py`, `tests/test_d1_catalogo.py` | `p05` (rechazo con mensaje comprensible): `bash scripts/pruebas.sh tests/test_d1_organizacion.py tests/test_d1_catalogo.py` |
| D9: función de servicio común | Formularios, importador y `cargar_demo` usan la misma validación del responsable | `tests/test_p11_responsable.py::test_funcion_de_servicio_comun_valida_la_seccion` | `p11` |
| Referencias inactivas al reimportar | Nivel 1 o valor de catálogo dados de baja no bloquean la reimportación: `REFERENCIA_INACTIVA`, valores conservados; un servicio nuevo con N1 inactivo no se crea | `tests/test_referencia_inactiva.py` | `p07`, `importacion`: `bash scripts/pruebas.sh tests/test_referencia_inactiva.py` |
| Importador: otro archivo, controles y dry-run | Con `--archivo` se registra el hash sin compararlo; controles 12/46 informativos o exigidos; `--dry-run` no guarda nada | `tests/test_p06_importacion.py` (`test_otro_archivo_…`, `test_controles_…`, `test_dry_run_…`) | `bash scripts/pruebas.sh -m importacion` |
| Historial de importaciones | Pantalla solo lectura (POST → 405) | `tests/test_importacion_pantalla.py::test_historial_es_solo_lectura` | `importacion` |
| Ficha y trazabilidad del catálogo | Atributos, valores originales, observaciones, etiqueta corregida (`Demostration`), mapeo inicial, restricciones | `tests/test_ficha_catalogo.py` | `bash scripts/pruebas.sh -m catalogo` |
| Datos de demostración | `cargar_demo` (≥3 asignaciones válidas, idempotente, no pisa asignaciones) y `crear_cuentas_demo` (idempotente, `--restablecer`, variables obligatorias) | `tests/test_cargar_demo.py`, `tests/test_crear_cuentas_demo.py` | `bash scripts/pruebas.sh -m demo`; `bash scripts/pruebas.sh tests/test_crear_cuentas_demo.py` |
| Migración de usuarios a puesto | Usuarios previos quedan en un puesto transitorio inactivo; base vacía no crea jerarquía | `tests/test_migracion_puesto.py` | `bash scripts/pruebas.sh tests/test_migracion_puesto.py` |
| Humo del entorno | Login responde, `/salud/` da 200, las pruebas usan `test_*` | `tests/test_humo.py` | `bash scripts/pruebas.sh -m humo` |
| Ciclo de harness | `scripts/verificar.sh` detecta errores en los logs de `web` aunque el contenedor esté healthy (fallo real del socket de gunicorn, corregido) | Paso «logs de web sin errores» de `scripts/verificar.sh`; evidencia en `docs/evidencias/ciclo-harness/` | `bash scripts/verificar.sh` |
