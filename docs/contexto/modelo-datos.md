# Modelo de datos — v2 (fase 3, decisiones D1–D9 tomadas el 2026-10-02)

> Documento de diseño previo a la implementación. Fuentes: `AGENTS.md` (§4, §5), `docs/contexto/enunciado.md`
> (§2, §3.2, §3.3, §3.4, §6) y `docs/contexto/analisis-excel.md` (hechos del Excel, SHA-256
> `de3b478a…dcf0`).
>
> - Las decisiones D1–D9 (sección 7) fueron tomadas por el usuario el 2026-10-02, revisándolas una por una
>   (D7 y D8 con ajustes). Donde el modelo aplica una de ellas, se indica con `→ Dn`. Las opciones descartadas se
>   conservan en la sección 7 como evidencia de las alternativas evaluadas.
> - Todo campo que no proviene del Excel ni del enunciado se marca **agregado por diseño**, con su motivo.
> - Motor: PostgreSQL 16. Framework: Django 5.2. Los nombres de tabla siguen la convención de Django
>   `<app>_<modelo>` (apps `cuentas`, `organizacion`, `catalogo`, `importacion`, según `AGENTS.md` §6).

---

## 1. Diagrama entidad-relación

```mermaid
erDiagram
    ORGANIZACION_EMPRESA ||--o{ ORGANIZACION_AREA : "contiene"
    ORGANIZACION_AREA ||--o{ ORGANIZACION_DEPARTAMENTO : "contiene"
    ORGANIZACION_DEPARTAMENTO ||--o{ ORGANIZACION_SECCION : "contiene"
    ORGANIZACION_SECCION ||--o{ ORGANIZACION_PUESTO : "contiene"
    ORGANIZACION_PUESTO ||--o{ CUENTAS_USUARIO : "ocupado por"

    CATALOGO_SERVICIONIVEL1 ||--o{ CATALOGO_SERVICIONIVEL2 : "agrupa"
    CATALOGO_CLASESERVICIO |o--o{ CATALOGO_SERVICIONIVEL2 : "clasifica"
    CATALOGO_CRITICIDAD |o--o{ CATALOGO_SERVICIONIVEL2 : "califica"
    CATALOGO_TIPOSERVICIO |o--o{ CATALOGO_SERVICIONIVEL2 : "tipifica"
    ORGANIZACION_SECCION |o--o{ CATALOGO_SERVICIONIVEL2 : "seccion responsable"
    CUENTAS_USUARIO |o--o{ CATALOGO_SERVICIONIVEL2 : "usuario responsable"

    CATALOGO_SERVICIONIVEL1 ||--o| IMPORTACION_ORIGENSERVICIO : "procede de"
    CATALOGO_SERVICIONIVEL2 ||--o| IMPORTACION_ORIGENSERVICIO : "procede de"
    IMPORTACION_EJECUCION ||--o{ IMPORTACION_ORIGENSERVICIO : "primera / ultima ejecucion"
    IMPORTACION_EJECUCION ||--o{ IMPORTACION_OBSERVACION : "genera"
    CATALOGO_SERVICIONIVEL1 |o--o{ IMPORTACION_OBSERVACION : "afecta a"
    CATALOGO_SERVICIONIVEL2 |o--o{ IMPORTACION_OBSERVACION : "afecta a"
    CUENTAS_USUARIO |o--o{ IMPORTACION_EJECUCION : "ejecuta"

    ORGANIZACION_EMPRESA {
        bigint id PK
        varchar codigo UK
        varchar nombre
        boolean activo
    }
    ORGANIZACION_AREA {
        bigint id PK
        bigint empresa_id FK
        varchar codigo "UK con empresa_id"
        varchar nombre
        boolean activo
    }
    ORGANIZACION_DEPARTAMENTO {
        bigint id PK
        bigint area_id FK
        varchar codigo "UK con area_id"
        varchar nombre
        boolean activo
    }
    ORGANIZACION_SECCION {
        bigint id PK
        bigint departamento_id FK
        varchar codigo "UK con departamento_id"
        varchar nombre
        boolean activo
    }
    ORGANIZACION_PUESTO {
        bigint id PK
        bigint seccion_id FK
        varchar codigo "UK con seccion_id"
        varchar nombre
        boolean activo
    }
    CUENTAS_USUARIO {
        bigint id PK
        varchar username UK
        varchar email UK
        varchar nombre
        varchar password "hash Argon2"
        varchar rol "ADMIN o CONSULTA"
        boolean is_active
        bigint puesto_id FK
    }
    CATALOGO_CLASESERVICIO {
        bigint id PK
        varchar codigo UK
        varchar etiqueta_original UK
        varchar etiqueta_mostrada
        boolean activo
    }
    CATALOGO_CRITICIDAD {
        bigint id PK
        varchar codigo UK
        varchar etiqueta_original UK
        varchar etiqueta_mostrada
        boolean activo
    }
    CATALOGO_TIPOSERVICIO {
        bigint id PK
        varchar codigo UK
        varchar etiqueta_original UK
        varchar etiqueta_mostrada
        boolean activo
    }
    CATALOGO_SERVICIONIVEL1 {
        bigint id PK
        varchar codigo UK
        varchar nombre
        varchar estado_revision
        boolean activo
    }
    CATALOGO_SERVICIONIVEL2 {
        bigint id PK
        varchar codigo UK
        varchar codigo_original UK
        bigint nivel1_id FK
        varchar nombre
        text activo_excel "texto original; NULL = desconocido"
        bigint clase_id FK
        bigint criticidad_id FK
        bigint tipo_id FK
        text descripcion
        varchar metrica
        numeric minimo
        numeric maximo
        varchar estado_revision
        bigint seccion_responsable_id FK
        bigint usuario_responsable_id FK
        boolean activo
    }
    IMPORTACION_EJECUCION {
        bigint id PK
        timestamptz iniciada_en
        char archivo_sha256
        varchar estado
        integer creados
        integer actualizados
        integer omitidos
        integer observados
    }
    IMPORTACION_ORIGENSERVICIO {
        bigint id PK
        bigint servicio_nivel1_id FK "UK"
        bigint servicio_nivel2_id FK "UK"
        varchar hoja
        int_array filas
        jsonb valores_originales
        jsonb transformaciones
    }
    IMPORTACION_OBSERVACION {
        bigint id PK
        bigint ejecucion_id FK
        varchar tipo
        varchar codigo_afectado
        int_array filas
        text detalle
        jsonb valores_conflicto
    }
    IMPORTACION_MAPEOCORRECCION {
        bigint id PK
        varchar ambito "UK con valor_original"
        text valor_original
        text valor_corregido
        text motivo
    }
```

Lectura de cardinalidades:

- Cada Área, Departamento, Sección, Puesto y Usuario tiene **exactamente un** padre (`||`); un padre tiene cero o
  muchos hijos (`o{`). Un puesto puede tener varios usuarios.
- Cada servicio nivel 2 tiene exactamente un nivel 1; clase, criticidad, tipo, sección responsable y usuario
  responsable son **cero o uno** (`|o`), porque las filas 99–101 no tienen atributos y los importados pueden quedar
  sin asignación.
- `IMPORTACION_ORIGENSERVICIO` pertenece a exactamente un servicio (nivel 1 **o** nivel 2); un servicio creado
  manualmente no tiene origen.
- `IMPORTACION_MAPEOCORRECCION` no tiene FK: es una tabla de reglas que el importador consulta por
  `(ambito, valor_original)`.
- No existe relación Usuario → Empresa: la empresa se deriva por
  `usuario.puesto.seccion.departamento.area.empresa` (`AGENTS.md` §4.9).

---

## 2. Convenciones comunes del diccionario

| Concepto | Implementación |
|---|---|
| PK | `id BIGINT GENERATED BY DEFAULT AS IDENTITY` (`BigAutoField` de Django) |
| FK | Restricción `FOREIGN KEY … DEFERRABLE INITIALLY DEFERRED` creada por Django, **sin** `ON DELETE` en la base (equivale a `NO ACTION`). En Django todas las FK usan `on_delete=PROTECT`: no hay borrado en cascada |
| Baja lógica | `activo BOOLEAN NOT NULL DEFAULT TRUE` (Usuario usa `is_active`, nombre requerido por Django). No se expone borrado físico en la interfaz |
| Texto obligatorio | `CHECK (btrim(col) <> '')` para que una cadena vacía o de espacios no cuente como valor |
| Auditoría | `creado_en TIMESTAMPTZ NOT NULL DEFAULT now()`, `actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()` (actualizado por Django con `auto_now`). **Agregado por diseño:** saber cuándo se dio de alta o modificó un registro; ayuda a P07 y P12 |
| Padre activo | No se puede expresar con CHECK (depende de otra fila). Se valida **en el servidor** (método `clean()` del modelo, invocado siempre mediante `full_clean()` en la capa de servicio) |
| Columnas abreviadas | Las columnas `creado_en`/`actualizado_en` se omiten en las tablas siguientes cuando solo repiten esta convención |

Abreviaturas: **N** = admite NULL; **NN** = NOT NULL; **UK** = UNIQUE.

---

## 3. Diccionario de datos

### 3.1 Organización (app `organizacion`)

#### `organizacion_empresa`

| Columna | Tipo PG | Nulo | Default | Clave | CHECK / nota |
|---|---|---|---|---|---|
| id | bigint identity | NN | identity | PK | |
| codigo | varchar(20) | NN | — | UK (global) | `btrim(codigo) <> ''` |
| nombre | varchar(200) | NN | — | | `btrim(nombre) <> ''` |
| activo | boolean | NN | `true` | | estado (baja lógica) |
| creado_en / actualizado_en | timestamptz | NN | `now()` | | agregado por diseño (ver §2) |

#### `organizacion_area`, `organizacion_departamento`, `organizacion_seccion`, `organizacion_puesto`

Las cuatro tablas tienen la misma forma; solo cambia la columna padre.

| Tabla | Columna padre (FK NN) | Referencia |
|---|---|---|
| `organizacion_area` | `empresa_id` | `organizacion_empresa(id)` |
| `organizacion_departamento` | `area_id` | `organizacion_area(id)` |
| `organizacion_seccion` | `departamento_id` | `organizacion_departamento(id)` |
| `organizacion_puesto` | `seccion_id` | `organizacion_seccion(id)` |

| Columna | Tipo PG | Nulo | Default | Clave | CHECK / nota |
|---|---|---|---|---|---|
| id | bigint identity | NN | identity | PK | |
| `<padre>_id` | bigint | **NN** | — | FK | NOT NULL impide huérfanos; FK impide padre inexistente |
| codigo | varchar(20) | NN | — | UK `(<padre>_id, codigo)` | `btrim(codigo) <> ''`. Nombre de restricción: `uq_<tabla>_padre_codigo` |
| nombre | varchar(200) | NN | — | | `btrim(nombre) <> ''` |
| activo | boolean | NN | `true` | | estado (baja lógica) |
| creado_en / actualizado_en | timestamptz | NN | `now()` | | agregado por diseño |

Validaciones en servidor (todas las tablas de organización):

- Alta o cambio de padre: el padre debe existir **y estar activo** (`AGENTS.md` §4.4).
- Desactivación con dependencias activas → **D1**: se rechaza y se muestra la lista de dependientes activos.
- Reactivación: solo si el padre está activo (agregado por diseño: evita un hijo activo bajo un padre inactivo).

#### `cuentas_usuario` (usuario personalizado, `AUTH_USER_MODEL = "cuentas.Usuario"`)

Se basa en `AbstractBaseUser` (aporta `password` y `last_login`) y **no** en `AbstractUser`, para no tener
`is_staff`/`is_superuser` que puedan contradecir `rol` (ver supuesto S6).

| Columna | Tipo PG | Nulo | Default | Clave | CHECK / nota |
|---|---|---|---|---|---|
| id | bigint identity | NN | identity | PK | |
| username | varchar(150) | NN | — | UK sobre `lower(username)` | `btrim(username) <> ''`. Unicidad sin distinguir mayúsculas |
| email | varchar(254) | NN | — | UK sobre `lower(email)` | Inicio de sesión con usuario **o** correo |
| nombre | varchar(200) | NN | — | | `btrim(nombre) <> ''` |
| password | varchar(128) | NN | — | | Hash `argon2$argon2id$…` con sal (formato de Django). Nunca se muestra al rol consulta |
| rol | varchar(10) | NN | `'CONSULTA'` | | `CHECK (rol IN ('ADMIN','CONSULTA'))`. Default al de menor privilegio |
| is_active | boolean | NN | `true` | | Baja lógica; el backend de autenticación rechaza `is_active = false` |
| puesto_id | bigint | **NN** | — | FK → `organizacion_puesto(id)` | Sin huérfanos. Puesto activo: validado en servidor |
| last_login | timestamptz | N | NULL | | Aportado por Django |
| creado_en / actualizado_en | timestamptz | NN | `now()` | | agregado por diseño |

Tablas del framework que se usan sin modificar: `django_session` (el cierre de sesión borra la fila con
`logout()` → `session.flush()`), `django_migrations`, `django_content_type`, `auth_permission`.

### 3.2 Catálogos de atributos (app `catalogo`)

#### `catalogo_claseservicio`, `catalogo_criticidad`, `catalogo_tiposervicio`

Misma forma para las tres tablas.

| Columna | Tipo PG | Nulo | Default | Clave | CHECK / nota |
|---|---|---|---|---|---|
| id | bigint identity | NN | identity | PK | |
| codigo | varchar(30) | NN | — | UK | Identificador estable sin espacios (`A_DEMANDA`, `VERY_LOW`, `DEMOSTRATION`…). `CHECK (codigo ~ '^[A-Z0-9_]+$')` |
| etiqueta_original | varchar(100) | NN | — | UK | Texto exacto de la lista del Excel (p. ej. `Demostration`). No editable desde la interfaz |
| etiqueta_mostrada | varchar(100) | NN | — | | Texto que ve el usuario. Igual a la original salvo que exista un mapeo de corrección. Única corrección: `Demostration` → `Demonstration` (tipo, H113) → **D7** |
| orden | smallint | NN | — | | **Agregado por diseño:** conservar el orden de la lista del Excel (filas 112–122); en criticidad expresa la escala Very Low → Very High. `CHECK (orden >= 0)` |
| fila_origen | integer | N | NULL | | **Agregado por diseño:** fila de la lista `E112:H122` de donde proviene; NULL si se creó en la aplicación |
| activo | boolean | NN | `true` | | Un valor inactivo no aparece en formularios nuevos |

Contenido esperado tras la importación (hecho del análisis §g): clase 2, criticidad 5, tipo 11.
Los catálogos solo se alimentan de las listas `E112:H122` o del mantenimiento hecho por un administrador; el
importador **nunca** crea entradas a partir de las columnas F, G y H de los servicios.
La lista de `ACTIVO` (`S`, `N`, columna E) **no** es tabla: son dos valores fijos que se controlan con CHECK.

#### Registro del mapeo de correcciones: `importacion_mapeocorreccion`

Una sola tabla para todas las correcciones de textos y códigos procedentes del Excel. Las filas se cargan desde
una migración de datos versionada (reproducible y revisable en Git), no a mano.

| Columna | Tipo PG | Nulo | Default | Clave | CHECK / nota |
|---|---|---|---|---|---|
| id | bigint identity | NN | identity | PK | |
| ambito | varchar(30) | NN | — | UK `(ambito, valor_original)` | `CHECK (ambito IN ('ETIQUETA_CLASE','ETIQUETA_CRITICIDAD','ETIQUETA_TIPO','NOMBRE_N1','NOMBRE_N2','CODIGO_N2'))` |
| valor_original | text | NN | — | | Texto exacto del Excel |
| valor_corregido | text | NN | — | | `CHECK (valor_corregido <> valor_original)` |
| celda_origen | varchar(20) | N | NULL | | Celda de referencia, p. ej. `H113`, `D100` |
| motivo | text | NN | — | | Justificación de la corrección |
| activo | boolean | NN | `true` | | Permite retirar una regla sin borrarla |

Uso: el importador aplica las reglas activas, guarda el valor corregido en el campo funcional
(`etiqueta_mostrada`, `nombre` o `codigo`) y deja el original en `etiqueta_original`, `codigo_original` o
`valor_originales` del origen, y una entrada en `transformaciones`.

Contenido inicial del mapeo (→ **D7**, **D5**): una sola fila activa,
`('ETIQUETA_TIPO', 'Demostration', 'Demonstration', 'H113', 'Error de escritura en la lista de tipos')`.
No hay filas `NOMBRE_N1`, `NOMBRE_N2` ni `CODIGO_N2`: los nombres de servicios y los códigos `SE.12.n` no se
corrigen. Los ámbitos se mantienen en el CHECK para poder registrar correcciones futuras de forma verificable.

### 3.3 Servicios (app `catalogo`)

#### `catalogo_servicionivel1`

| Columna | Tipo PG | Nulo | Default | Clave | CHECK / nota |
|---|---|---|---|---|---|
| id | bigint identity | NN | identity | PK | |
| codigo | varchar(20) | NN | — | UK | Columna A, texto exacto (`SE.01` … `SE.12`). `btrim(codigo) <> ''` |
| nombre | varchar(200) | NN | — | | Columna B. SE.12 → `Suministrar Analitica` (B99), `estado_revision = PENDIENTE_REVISION` → **D3** |
| estado_revision | varchar(20) | NN | `'SIN_OBSERVACIONES'` | | **Agregado por diseño:** SE.12 tiene conflicto de nombre y debe quedar marcado. `CHECK (estado_revision IN ('SIN_OBSERVACIONES','PENDIENTE_REVISION','REVISADO'))` |
| activo | boolean | NN | `true` | | Estado del registro (baja lógica) |
| creado_en / actualizado_en | timestamptz | NN | `now()` | | agregado por diseño |

#### `catalogo_servicionivel2`

| Columna | Tipo PG | Nulo | Default | Clave | CHECK / nota |
|---|---|---|---|---|---|
| id | bigint identity | NN | identity | PK | |
| codigo | varchar(20) | NN | — | UK | Código funcional. En importados es igual a `codigo_original` (sin normalizar, también `SE.12.1`–`SE.12.3`) → **D5** |
| codigo_original | varchar(20) | N | NULL | UK parcial (`WHERE codigo_original IS NOT NULL`) | Columna C, texto exacto (`SE.12.1`). NULL solo en servicios creados en la aplicación. No editable. **Clave natural de importación** (§6) |
| nivel1_id | bigint | **NN** | — | FK → `catalogo_servicionivel1(id)` | Todo N2 pertenece a un N1. SE.12.3 → SE.12 por prefijo de código, con observación y `PENDIENTE_REVISION` → **D4** |
| nombre | varchar(200) | NN | — | | Columna D. `btrim(nombre) <> ''` |
| activo_excel | text | N | NULL | | Columna E, **texto original tal cual** (sin recortar ni cambiar mayúsculas). `S` y `N` son los valores reconocidos (comparación exacta); cualquier otro valor no vacío se guarda igual y genera la observación `VALOR_NO_RECONOCIDO`; solo la celda vacía se guarda como NULL (filas 99–101), y la interfaz la muestra como "Desconocido". `CHECK (activo_excel IS NULL OR activo_excel <> '')`: la cadena vacía nunca sustituye a NULL. Sin `CHECK IN ('S','N')`, porque bloquearía valores originales → **D6**, **D8**. Formulario: ofrece S, N o Desconocido; un valor no reconocido existente se muestra y se conserva salvo que el administrador lo cambie |
| clase_id | bigint | N | NULL | FK → `catalogo_claseservicio(id)` | Columna F. NULL = vacío (desconocido, **D6**) o valor fuera de lista → regla de valores fuera de lista (§3.3) |
| criticidad_id | bigint | N | NULL | FK → `catalogo_criticidad(id)` | Columna G. Ídem |
| tipo_id | bigint | N | NULL | FK → `catalogo_tiposervicio(id)` | Columna H. Ídem |
| descripcion | text | N | NULL | | Columna I. NULL si vacía (nunca `''`). I5 se guarda tal cual, como dato |
| metrica | varchar(200) | N | NULL | | Columna J |
| minimo | numeric(14,4) | N | NULL | | Columna K. Vacío → NULL, nunca 0 |
| maximo | numeric(14,4) | N | NULL | | Columna L. Vacío → NULL, nunca 0 |
| estado_revision | varchar(20) | NN | `'SIN_OBSERVACIONES'` | | `CHECK (estado_revision IN ('SIN_OBSERVACIONES','PENDIENTE_REVISION','REVISADO'))`. Filas 99–101 → `PENDIENTE_REVISION` |
| seccion_responsable_id | bigint | N | NULL | FK → `organizacion_seccion(id)` | Dato nuevo del parcial (no viene del Excel). Sección activa: servidor |
| usuario_responsable_id | bigint | N | NULL | FK → `cuentas_usuario(id)` | Opcional. Debe pertenecer a la sección responsable; validado en servidor → **D9** |
| activo | boolean | NN | `true` | | Estado del registro (baja lógica). Todo servicio importado entra con `true`, aunque `activo_excel` sea `N`, desconocido o no reconocido → **D8** |
| creado_en / actualizado_en | timestamptz | NN | `now()` | | agregado por diseño |

Regla de valores fuera de lista en F, G y H (clase, criticidad, tipo; parte de v2):

1. La celda se compara de forma **exacta** contra `etiqueta_original` del catálogo correspondiente (sin recortar
   espacios ni cambiar mayúsculas), igual que `activo_excel`.
2. Si no hay coincidencia, **no** se crea una entrada nueva en el catálogo: la FK queda en NULL.
3. El servicio queda con `estado_revision = PENDIENTE_REVISION` y se registra una observación `VALOR_NO_RECONOCIDO`
   con columna, fila y valor (`celdas = {F12}`, `filas = {12}`, `valores_conflicto = {"columna": "F", "fila": 12, "valor": "…"}`).
4. El valor original se conserva en `importacion_origenservicio.valores_originales`; la ficha del servicio lo muestra
   junto a la observación (p. ej. "Clase: sin valor reconocido — original en Excel: '…'").

Motivo: los catálogos son opciones controladas (enunciado §3.3); crear valores en silencio los contaminaría y
descartar el valor perdería el dato original. Con el Excel actual no ocurre: E–H no tienen valores no vacíos fuera
de lista (análisis §g).

Restricciones de tabla:

| Nombre | Definición | Motivo |
|---|---|---|
| `ck_n2_minimo_le_maximo` | `CHECK (minimo IS NULL OR maximo IS NULL OR minimo <= maximo)` | Regla §4.6; P09. También se valida en el formulario para dar mensaje comprensible |
| `ck_n2_usuario_requiere_seccion` | `CHECK (usuario_responsable_id IS NULL OR seccion_responsable_id IS NOT NULL)` | No puede haber usuario responsable sin sección responsable |
| `uq_n2_codigo` | `UNIQUE (codigo)` | Código único en su entidad |
| `uq_n2_codigo_original` | `UNIQUE (codigo_original) WHERE codigo_original IS NOT NULL` | Idempotencia de la importación |

Índices adicionales (búsqueda y filtros, P10): `nombre` y `codigo` con `gin_trgm_ops` (extensión `pg_trgm`,
**agregado por diseño** para búsqueda parcial eficiente; opcional, con 46 registros basta `ILIKE`), y B-tree en
`nivel1_id`, `clase_id`, `criticidad_id`, `tipo_id`, `activo`, `activo_excel` (Django crea los de FK
automáticamente).

Filtros del listado de servicios (→ **D8**, ajuste del usuario). `activo` y `activo_excel` se filtran **por
separado**, cada uno con su propio control, para que un servicio como SE.05.01 (`ACTIVO = N`, registro activo) se
pueda localizar:

| Filtro | Campo | Opciones | Condición SQL |
|---|---|---|---|
| Estado del registro | `activo` | Activos (por defecto) / Dados de baja / Todos | `activo = true` / `activo = false` / sin condición |
| ACTIVO (Excel) | `activo_excel` | S / N / Desconocido / Otros / Todos (por defecto) | `= 'S'` / `= 'N'` / `IS NULL` / `IS NOT NULL AND activo_excel NOT IN ('S','N')` / sin condición |
| Nivel 1, clase, criticidad, tipo | FK | Valores del catálogo + "Sin dato" (→ D6; incluye valores fuera de lista, identificables por su observación) | `= id` / `IS NULL` |
| Estado de revisión | `estado_revision` | Los tres valores / Todos | `= valor` |

### 3.4 Trazabilidad (app `importacion`)

#### `importacion_ejecucion`

Una fila por cada ejecución del importador (también las repetidas: así P07 es trazable).

| Columna | Tipo PG | Nulo | Default | Clave | CHECK / nota |
|---|---|---|---|---|---|
| id | bigint identity | NN | identity | PK | |
| iniciada_en | timestamptz | NN | `now()` | | Fecha de la ejecución |
| finalizada_en | timestamptz | N | NULL | | `CHECK (finalizada_en IS NULL OR finalizada_en >= iniciada_en)` |
| archivo_nombre | varchar(255) | NN | — | | p. ej. `data/CatalogoServicios.xlsx` |
| archivo_sha256 | char(64) | NN | — | | `CHECK (archivo_sha256 ~ '^[0-9a-f]{64}$')`. Permite comprobar que se importó el archivo original |
| hoja | varchar(100) | NN | `'Servicios Externos'` | | |
| estado | varchar(10) | NN | `'EN_CURSO'` | | `CHECK (estado IN ('EN_CURSO','EXITOSA','FALLIDA'))`. **Agregado por diseño:** distinguir una ejecución abortada |
| creados | integer | NN | `0` | | `CHECK (creados >= 0)` — registros nuevos (N1 + N2 + valores de catálogo) |
| actualizados | integer | NN | `0` | | `CHECK (actualizados >= 0)` — registros existentes con al menos un campo del Excel cambiado |
| sin_cambios | integer | NN | `0` | | **Agregado por diseño:** en una repetición, creados = actualizados = 0 y todo cae aquí; sin esta columna el resumen no cuadra |
| omitidos | integer | NN | `0` | | `CHECK (omitidos >= 0)` — filas de 5–101 que no generan registro (continuación, filas sin código) |
| observados | integer | NN | `0` | | `CHECK (observados >= 0)` — número de observaciones emitidas |
| total_n1 | integer | N | NULL | | **Agregado por diseño:** control de 12 códigos N1 encontrados |
| total_n2 | integer | N | NULL | | **Agregado por diseño:** control de 46 códigos N2 encontrados |
| detalle_conteos | jsonb | NN | `'{}'` | | **Agregado por diseño:** desglose por entidad `{"nivel1": {"creados": …}, "nivel2": {…}, "clase": {…}}` |
| ejecutada_por_id | bigint | N | NULL | FK → `cuentas_usuario(id)` | **Agregado por diseño:** NULL si se ejecutó por comando |
| mensaje_error | text | N | NULL | | Solo si `estado = 'FALLIDA'` |

#### `importacion_origenservicio`

Origen **vigente** de cada servicio importado (uno por servicio). El histórico por ejecución queda en
`importacion_ejecucion` + `importacion_observacion` + `primera/ultima_ejecucion`.

| Columna | Tipo PG | Nulo | Default | Clave | CHECK / nota |
|---|---|---|---|---|---|
| id | bigint identity | NN | identity | PK | |
| servicio_nivel1_id | bigint | N | NULL | FK, UK | |
| servicio_nivel2_id | bigint | N | NULL | FK, UK | `CHECK (num_nonnulls(servicio_nivel1_id, servicio_nivel2_id) = 1)` |
| hoja | varchar(100) | NN | — | | `Servicios Externos` |
| filas | integer[] | NN | — | | Filas físicas cubiertas, p. ej. `{5,6,7}` para SE.01.01; `{99,100}` para SE.12. `CHECK (cardinality(filas) >= 1)` |
| rangos_combinados | text[] | NN | `'{}'` | | p. ej. `{C5:C7,D5:D7,J5:J7}` |
| valores_originales | jsonb | NN | — | | Valor bruto por columna con su celda: `{"C": {"celda": "C5", "valor": "SE.01.01"}, "I": {"celda": "I5", "valor": "Revele su rollo "}, "K": {"celda": "K5", "valor": 1.0}, …}`. Para SE.12 guarda **ambos** nombres (B99 y B100) |
| transformaciones | jsonb | NN | `'[]'` | | Lista de transformaciones aplicadas: `[{"campo": "minimo", "regla": "vacio_a_null"}, {"campo": "nivel1", "regla": "padre_por_prefijo"}, …]` |
| primera_ejecucion_id | bigint | NN | — | FK → `importacion_ejecucion(id)` | |
| ultima_ejecucion_id | bigint | NN | — | FK → `importacion_ejecucion(id)` | |
| ultima_accion | varchar(12) | NN | — | | `CHECK (ultima_accion IN ('CREADO','ACTUALIZADO','SIN_CAMBIOS'))` |

#### `importacion_observacion`

| Columna | Tipo PG | Nulo | Default | Clave | CHECK / nota |
|---|---|---|---|---|---|
| id | bigint identity | NN | identity | PK | |
| ejecucion_id | bigint | NN | — | FK → `importacion_ejecucion(id)` | |
| tipo | varchar(40) | NN | — | | `CHECK (tipo IN ('CONFLICTO_NOMBRE_N1','FILA_SIN_CODIGO','PADRE_POR_PREFIJO','ATRIBUTOS_AUSENTES','CODIGO_FORMATO_NO_ESTANDAR','CORRECCION_APLICADA','POSIBLE_ERROR_ESCRITURA','VALOR_NO_RECONOCIDO','TEXTO_CON_FORMA_DE_INSTRUCCION','ESPACIOS_EN_TEXTO','AUSENCIA_EN_CONTINUACION','CONTROL_CONTEO'))` |
| severidad | varchar(12) | NN | `'ADVERTENCIA'` | | **Agregado por diseño.** `CHECK (severidad IN ('INFO','ADVERTENCIA','ERROR'))` |
| codigo_afectado | varchar(20) | N | NULL | | Código tal como en el Excel; NULL en filas sin código (42, 67) |
| servicio_nivel1_id | bigint | N | NULL | FK | **Agregado por diseño:** mostrar observaciones en la ficha |
| servicio_nivel2_id | bigint | N | NULL | FK | Ídem |
| filas | integer[] | NN | — | | `CHECK (cardinality(filas) >= 1)` |
| celdas | text[] | NN | `'{}'` | | p. ej. `{B99,B100}` |
| detalle | text | NN | — | | Descripción legible |
| valores_conflicto | jsonb | N | NULL | | p. ej. `{"B99": "Suministrar Analitica", "B100": "Mantener Tableros de Control"}` |
| regla_aplicada | text | N | NULL | | **Agregado por diseño:** regla documentada que resolvió el caso (enunciado §3.4.6) |

Observaciones previstas con el Excel actual (aplicando D2–D7):

| Tipo | Código / filas | Origen de la regla |
|---|---|---|
| `CONFLICTO_NOMBRE_N1` | SE.12, filas 99–100, `{B99, B100}` | D3 |
| `FILA_SIN_CODIGO` | sin código, fila 42 y fila 67 (una observación cada una, con E–H en `valores_conflicto`) | D2 |
| `PADRE_POR_PREFIJO` | SE.12.3, fila 101 | D4 |
| `ATRIBUTOS_AUSENTES` | SE.12.1, SE.12.2, SE.12.3 (filas 99–101) | D6 |
| `CODIGO_FORMATO_NO_ESTANDAR` | SE.12.1, SE.12.2, SE.12.3 | D5 |
| `CORRECCION_APLICADA` | `Demostration` → `Demonstration` (H113) | D7 |
| `POSIBLE_ERROR_ESCRITURA` | SE.12.2, `D100` = `Suministrar Análsis de Información` (no se corrige) | D7 (ajuste) |
| `TEXTO_CON_FORMA_DE_INSTRUCCION`, `ESPACIOS_EN_TEXTO` | SE.01.01, I5 | AGENTS.md §9 |
| `AUSENCIA_EN_CONTINUACION` | SE.01.01, I/K/L en filas 6–7 | §3.4.6 |
| `CONTROL_CONTEO` | 12 N1 / 46 N2 (severidad `INFO` si pasa) | §3.4 |
| `VALOR_NO_RECONOCIDO` | Ninguna con el Excel actual: en E–H no hay valores no vacíos fuera de lista (análisis §g). Se emitiría por cada celda E con valor distinto de `S`/`N`, o F/G/H sin coincidencia exacta en el catálogo, con columna, fila y valor en `valores_conflicto` | D8 (ajuste); regla F–H (§3.3) |

---

## 4. Mapeo de columnas del Excel (hoja `Servicios Externos`, encabezados A4:L4)

| Col | Encabezado | Destino | Tratamiento |
|---|---|---|---|
| A | COD.N1 | `catalogo_servicionivel1.codigo`; FK `servicionivel2.nivel1_id` | Valor de la celda principal **dentro de su rango** `A…`. Texto exacto. Fila 101 vacía → padre SE.12 por prefijo del código (D4) |
| B | SERVICIO - Nivel 1 | `servicionivel1.nombre` | Celda principal del rango `B…`. SE.12: nombre `Suministrar Analitica` (B99); B99 y B100 en `valores_originales` + observación (D3) |
| C | COD.N2 | `servicionivel2.codigo_original` y `codigo` | Solo una celda C con valor propio (no continuación) crea un servicio. Texto exacto, sin normalizar (D5); filas 42 y 67 no crean servicio (D2) |
| D | SERVICIO - Nivel 2 | `servicionivel2.nombre` | Celda principal del rango `D…`. Sin correcciones; `Análsis` (D100) genera observación `POSIBLE_ERROR_ESCRITURA` (D7) |
| E | ACTIVO | `servicionivel2.activo_excel` | Texto original tal cual. `S`/`N` reconocidos; otro valor no vacío → se guarda igual + observación `VALOR_NO_RECONOCIDO`; vacío → NULL, mostrado como "Desconocido" (D6, D8). No modifica la baja lógica. Fila principal del servicio |
| F | CLASE DE SERVICIO | `servicionivel2.clase_id` → `catalogo_claseservicio` (comparación exacta con `etiqueta_original`) | Vacío → NULL, desconocido (D6). Valor fuera de lista → FK NULL + `PENDIENTE_REVISION` + observación `VALOR_NO_RECONOCIDO`; original en `valores_originales`; nunca se crea en el catálogo. Lista `F112:F113` alimenta el catálogo |
| G | CRITICIDAD | `servicionivel2.criticidad_id` → `catalogo_criticidad` | Ídem que F; lista `G112:G116` |
| H | TIPO DE SERVICIO | `servicionivel2.tipo_id` → `catalogo_tiposervicio` | Ídem que F; lista `H112:H122`. `Demostration` se conserva en `etiqueta_original` y se muestra `Demonstration` (D7) |
| I | Descripción | `servicionivel2.descripcion` | No combinada: valor de la fila principal. Vacío → NULL. I5 se conserva como dato y genera observación `TEXTO_CON_FORMA_DE_INSTRUCCION` |
| J | Métrica | `servicionivel2.metrica` | Celda principal del rango `J…` o de la fila principal |
| K | Minimo | `servicionivel2.minimo` | Número → `Decimal(str(valor))`; vacío → NULL (nunca 0). Texto no numérico → observación y NULL |
| L | Maximo | `servicionivel2.maximo` | Ídem. Si ambos existen y `minimo > maximo` → observación `ERROR` y el servicio no se guarda con esos valores |

Además, en todos los servicios: hoja, filas, rangos y valores brutos A–L → `importacion_origenservicio`.
Fuera de A–L: filas 1–2 (títulos) se ignoran; `E111:H111` (`OPCIONES`) y `E112:H122` alimentan catálogos, nunca
servicios.

---

## 5. Restricciones del enunciado → implementación

| Restricción (fuente) | Base de datos | Servidor (Django) | Prueba prevista |
|---|---|---|---|
| Código de Empresa único (§3.2) | `UNIQUE (codigo)` | `validate_unique` con mensaje | P05 |
| Código único dentro del padre (§3.2) | `UNIQUE (<padre>_id, codigo)` en Área/Depto/Sección/Puesto | Mensaje comprensible | P05 |
| Código N1 y N2 único (§3.3) | `UNIQUE (codigo)` en ambas tablas | Ídem | P05 |
| Un único padre, sin huérfanos (§3.2) | FK `NOT NULL` | Formularios con opciones controladas | P04, P05 |
| Referencia inexistente (§3.3, P05) | FK | `ModelChoiceField` rechaza id inexistente | P05 |
| Sin asociaciones nuevas con padres inactivos (§3.2) | — (no expresable con CHECK) | `clean()` verifica `padre.activo` / `puesto.activo` / `seccion.activo` | P04 (caso negativo) |
| Política de desactivación con dependencias (§3.2) | — | Función de desactivación que rechaza si hay dependientes activos y los lista (D1) | P04 (caso negativo) |
| Baja lógica, sin borrado silencioso (§3.2) | Columna `activo`/`is_active`; FK sin cascada | Sin vista de borrado; `PROTECT` | revisión + P04 |
| Empresa del usuario derivada (§3.2) | No existe columna `empresa_id` en usuario | Propiedad calculada `usuario.empresa` | P04 |
| Usuario o correo único (§3.2) | `UNIQUE (lower(username))`, `UNIQUE (lower(email))` | Backend que acepta usuario o correo | P01, P05 |
| Hash con sal, no reversible (§3.1) | `password varchar(128)` | `PASSWORD_HASHERS` con Argon2 primero | P01 + inspección del valor guardado |
| Usuario inactivo sin acceso (§3.1) | `is_active` | `ModelBackend.user_can_authenticate`; sesiones existentes dejan de ser válidas en la siguiente petición | P02 |
| Cierre de sesión invalida la sesión (§3.1) | `django_session` | `logout()` borra la sesión | P02 |
| Rol consulta solo lectura; sin hashes (§3.1) | `CHECK (rol IN …)` | Decorador/mixin por rol en cada vista de escritura; formularios/plantillas sin `password` | P03 |
| Opciones controladas de clase/criticidad/tipo (§3.3) | FK a tablas de catálogo | `ModelChoiceField` con `activo = true`; el importador no crea entradas: valor fuera de lista → FK NULL + `PENDIENTE_REVISION` + `VALOR_NO_RECONOCIDO` | P05, P10; caso de importación con valor fuera de lista (P08) |
| `minimo <= maximo` (§3.3) | `ck_n2_minimo_le_maximo` | `clean()` del formulario/modelo | P09 |
| Ausente ≠ 0 (§3.3) | Columnas `NULL` sin default numérico | Importador: vacío → `None` | P08 |
| ACTIVO: conservar valores desconocidos como tales (§2) | `activo_excel text` sin lista cerrada; `CHECK (activo_excel <> '')` | Importador guarda el texto original y observa `VALOR_NO_RECONOCIDO`; vacío → NULL | P08 |
| N2 pertenece a N1 (§3.3) | `nivel1_id NOT NULL` + FK | — | P06 |
| Responsable pertenece a la sección (§3.3) | `ck_n2_usuario_requiere_seccion` (parcial) | `clean()` + función de servicio común; se rechaza mover al responsable a un puesto de otra sección (D9) | P11 |
| Filtros por estado del registro y por ACTIVO del Excel (§3.3, ajuste D8) | Índices en `activo` y `activo_excel` | Dos filtros independientes en el listado (§3.3) | P10 (SE.05.01 localizable con ACTIVO = N) |
| Importados pueden quedar sin asignación (§3.3) | `seccion_responsable_id` NULL | — | P06 |
| ≥ 3 asignaciones demo (§3.3) | — | Comando de datos demo | verificación del comando |
| Conservar todos los campos del Excel (§3.3) | Columnas A–L (§4) + `valores_originales` | — | P06, P08 |
| Importación repetible sin duplicados (§3.4) | `UNIQUE` en claves naturales (§6) | `update_or_create` por clave natural en una transacción | P07 |
| Resumen creados/actualizados/omitidos/observados (§3.4) | `importacion_ejecucion` | Importador | P06, P07 |
| Celdas combinadas (§3.4.1) | `rangos_combinados`, `filas` | Lectura de rangos de openpyxl | P06 |
| SE.12 sin duplicar código (§3.4.2) | `UNIQUE (codigo)` en N1 | Nombre `Suministrar Analitica` + observación (D3) | P08 |
| Códigos SE.12.n como texto (§3.4.3) | `varchar`, `codigo_original` | Lectura como `str`, sin normalizar (D5) | P08 |
| Atributos incompletos 99–101 (§3.4.4) | FK/columnas NULL, `estado_revision` | NULL + `PENDIENTE_REVISION` (D6) | P08 |
| Filas de continuación y sin código (§3.4.5) | — | Clasificación por columna C; filas 42 y 67 omitidas con observación (D2) | P06 |
| Trazabilidad (§3.4.6) | `importacion_origenservicio`, `importacion_observacion` | Importador | P06–P08 |
| Correcciones de etiquetas con mapeo (§2) | `etiqueta_original` + `importacion_mapeocorreccion` | Importador aplica reglas | P06 |
| 12 N1 y 46 N2 (§3.4) | — | Controles `total_n1`/`total_n2`; la ejecución falla si no coinciden | P06 |
| Persistencia (§5) | Volumen de PostgreSQL | — | P12 |

---

## 6. Clave natural para la importación idempotente

| Entidad | Clave natural | Garantía en BD | Comentario |
|---|---|---|---|
| Servicio nivel 1 | `codigo` = valor de A (texto exacto) | `UNIQUE (codigo)` | SE.12 aparece en dos filas pero es una sola clave → un solo registro |
| Servicio nivel 2 | `codigo_original` = valor de C (texto exacto, sin normalizar) | `UNIQUE (codigo_original) WHERE NOT NULL` | Se usa el original y no `codigo` para que la clave no dependa de una normalización futura (hoy, por D5, ambos coinciden) |
| Clase / criticidad / tipo | `etiqueta_original` (texto exacto de la lista) | `UNIQUE (etiqueta_original)` | No depende de `etiqueta_mostrada` (D7) |
| Origen del servicio | FK al servicio | `UNIQUE` en cada FK | Se actualiza en cada ejecución |
| Mapeo de corrección | `(ambito, valor_original)` | `UNIQUE` | Cargado por migración de datos |
| Ejecución / observación | — (siempre se insertan) | — | Son el historial; repetir agrega una ejecución nueva, no registros funcionales |

Procedimiento: toda la ejecución en una transacción (`transaction.atomic`); por cada clave se busca el registro;
si no existe → `CREADO`; si existe y algún campo procedente del Excel difiere → `ACTUALIZADO` (con valor anterior y
nuevo en `transformaciones`); si no → `SIN_CAMBIOS`. Resultado esperado de una segunda ejecución sobre el mismo
archivo: `creados = 0`, `actualizados = 0`.

---

## 7. Decisiones tomadas (v2, 2026-10-02)

El usuario revisó cada decisión por separado; D7 y D8 se aceptaron con ajustes. Se conservan las opciones
evaluadas como evidencia de las alternativas descartadas.

### D1. Desactivación de registros con dependencias activas — DECIDIDA: opción A

Aplica a la jerarquía organizacional, a Sección con servicios asignados, a Usuario responsable de servicios, a
N1 con N2 activos y a valores de catálogo en uso.

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. Rechazar** si hay dependientes activos; el mensaje lista cuáles | Simple, explícito, nada cambia sin que el usuario lo vea; fácil de probar | Desactivar una rama completa exige ir de abajo hacia arriba |
| **B. Cascada con confirmación**: pantalla con el resumen de afectados; al confirmar se desactivan todos en una transacción y se registra el lote | Cómodo para ramas grandes; sigue sin borrar nada | Requiere tabla adicional de lotes de baja (agregado por diseño) para auditar y reactivar; más código y pruebas; decidir qué pasa con servicios asignados a una sección desactivada |
| **C. Permitir** desactivar el padre dejando hijos activos (solo se bloquean asociaciones nuevas) | Mínimo esfuerzo | Estado incoherente (hijos activos bajo padre inactivo); difícil de justificar ante "política coherente" |

Enunciado §3.2: "documentar e implementar una política coherente … sin eliminar información de manera silenciosa".
A y B lo cumplen.

**Decisión: A.** Se rechaza desactivar un registro con dependientes activos y se muestra la lista de dependientes.
**Motivo:** evita registros huérfanos o asociados a padres inactivos sin borrar ni cambiar información en silencio.

### D2. Filas 42 y 67 (con E–H, sin código N2, fuera de combinación) — DECIDIDA: opción A

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. Omitir** como servicio; contar como omitidas y emitir observación `FILA_SIN_CODIGO` con sus valores E–H en `valores_conflicto` | Cumple "evitar asignarla automáticamente"; conserva los 46; los valores quedan como evidencia | Los valores de la fila solo viven en la observación (son idénticos a los del servicio anterior, así que no se pierde información funcional) |
| **B. Anexarlas** al servicio anterior (SE.06.05 / SE.09.01) como si continuaran su rango | Explica las filas | Contradice el enunciado §3.4.5 (asignación automática sin rango que la respalde) |
| **C. Crear un servicio N2** con código sintético | No pierde la fila | Inventa un código; rompe el control de 46 |

**Decisión: A.** Las filas 42 y 67 no crean servicios: se cuentan como omitidas y se registra una observación
`FILA_SIN_CODIGO` con sus valores E–H.
**Motivo:** el enunciado (§3.4.5) prohíbe asignarlas automáticamente a otro servicio.

### D3. Nombre canónico de SE.12 — DECIDIDA: opción A

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. `Suministrar Analitica`** (B99) + ambos valores en `valores_originales` + observación `CONFLICTO_NOMBRE_N1` + `estado_revision = PENDIENTE_REVISION` | Es la primera aparición; no coincide con el nombre de ningún hijo; "Analítica" describe a los tres hijos (tableros y análisis) | Lleva el error de tilde (se combina con D7) |
| **B. `Mantener Tableros de Control`** (B100) | Es el último valor leído | Es idéntico al hijo SE.12.3 (D101): probable copia; describe solo a un hijo |
| **C. Mantener el código con nombre provisional** (p. ej. "SE.12 — nombre en revisión") | No toma partido | Inventa un nombre que no está en el Excel |

Enunciado §3.4.2 exige elegir y justificar, conservar ambos valores y emitir observación; las tres opciones guardan
evidencia, solo A y B usan un valor del archivo.

**Decisión: A.** Nombre canónico `Suministrar Analitica` (B99); se conservan ambos nombres como evidencia, observación
`CONFLICTO_NOMBRE_N1` y `estado_revision = PENDIENTE_REVISION`.
**Motivo:** es la primera fila del grupo, como en los otros 11 grupos; abarca a los tres hijos; y B100 es idéntico al
nombre del hijo SE.12.3, lo que sugiere un error de copiado.

### D4. Padre de SE.12.3 (fila 101, A y B vacías, sin combinación) — DECIDIDA: opción A

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. Por prefijo del código** (`SE.12.3` → `SE.12`), con observación `PADRE_POR_PREFIJO`, transformación registrada y `estado_revision = PENDIENTE_REVISION` | Regla explícita y verificable; cumple "todo N2 pertenece a un N1"; conserva 12/46 | Es una inferencia, no un dato de celda |
| **B. Por adyacencia** (heredar A de la fila anterior) | Mismo resultado aquí | Equivale a propagar valores fuera de un rango, lo que el enunciado §3.4.1 prohíbe sin regla explícita; generalizaría mal |
| **C. N1 comodín** ("SIN NIVEL 1") o no importarlo | No infiere | El comodín crea un 13.º N1 inexistente; no importarlo rompe los 46 |

**Decisión: A.** SE.12.3 se asigna a SE.12 por prefijo de código, con observación `PADRE_POR_PREFIJO` y
`estado_revision = PENDIENTE_REVISION`. La regla solo se aplica cuando A está vacía y el prefijo corresponde a un N1
existente.
**Motivo:** regla explícita y verificable que respeta "todo N2 pertenece a un N1" y conserva 12/46.

### D5. Normalización de códigos `SE.12.1`–`SE.12.3` — DECIDIDA: opción A

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. No normalizar**: `codigo = codigo_original = 'SE.12.1'`; observación `CODIGO_FORMATO_NO_ESTANDAR` | Máxima fidelidad; sin mapeo; lo que se busca es lo que dice el Excel | Formato mixto; orden alfabético puede no ser el natural en otros casos |
| **B. Normalizar** a `SE.12.01`…; `codigo_original` conserva el texto; tres filas `CODIGO_N2` en el mapeo | Formato uniforme `SE.NN.NN` | Dos códigos por servicio; la búsqueda debe cubrir ambos; más pruebas |
| **C. No normalizar + columna de orden** calculada | Fidelidad y orden natural | Columna adicional (agregado por diseño) para un problema que con 46 filas apenas existe |

Enunciado §3.4.3: conservar como texto; normalizar solo con original y mapeo verificable.

**Decisión: A.** No se normalizan `SE.12.1`, `SE.12.2` y `SE.12.3`; se registra la observación
`CODIGO_FORMATO_NO_ESTANDAR`.
**Motivo:** máxima fidelidad al Excel sin necesidad de mapeo de códigos.

### D6. Representación de valores desconocidos (filas 99–101: E, F, G, H, J; y en general) — DECIDIDA: opción A

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. NULL** en la columna/FK + `estado_revision = PENDIENTE_REVISION` + observación `ATRIBUTOS_AUSENTES`; la interfaz muestra "Sin dato en el Excel" y ofrece el filtro "sin valor" | No inventa valores; coherente con regla §4.7; NULL ya significa "desconocido" en SQL | Formularios y filtros deben tratar el caso NULL explícitamente |
| **B. Valor `DESCONOCIDO`** en cada catálogo y en `activo_excel` | FK siempre informada; filtros uniformes | Agrega a los catálogos un valor que no está en las listas del Excel; podría elegirse por error al crear servicios |
| **C. NULL + bandera booleana por campo** (`clase_desconocida`, …) | Explícito | Redundante con NULL; puede contradecirse |

Enunciado §3.4.4: "valores desconocidos o estado de revisión explícito; no inventar".

**Decisión: A.** Las ausencias se guardan como NULL con `estado_revision = PENDIENTE_REVISION` y observación
`ATRIBUTOS_AUSENTES`; nunca 0 ni valores inventados.
**Motivo:** no se agregan a los catálogos valores que no existen en el Excel (regla §4.7 de AGENTS.md).

### D7. Qué errores de escritura se corrigen — DECIDIDA: opción B con ajuste

Candidatos: `Demostration` (H113), `Análsis` (D100), `Analitica` (B99), `Area 8`/`Area 9` (D50, D55), espacio
final en I5.

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. No corregir nada**; solo observaciones | Fidelidad total; mapeo vacío | La interfaz muestra errores |
| **B. Corregir solo etiquetas de catálogo** (`Demostration` → `Demonstration` en `etiqueta_mostrada`), registrada en el mapeo | Es exactamente el caso que menciona el enunciado §2; mínimo riesgo | Los nombres de servicios siguen con errores |
| **C. Corregir catálogo + nombres** (`Análisis`, `Analítica`, `Área 8/9`), todo en el mapeo con celda y motivo | Interfaz limpia | Más reglas; mayor riesgo de "corregir" algo que era intencional; las pruebas deben comprobar original y corregido |

En las tres opciones: I5 se guarda sin recortar (es dato y evidencia).

**Decisión: B con ajuste.** Solo se corrige `Demostration` → `Demonstration` en `etiqueta_mostrada`, registrado en
`importacion_mapeocorreccion` (observación `CORRECCION_APLICADA`). **Ajuste:** `Análsis` (D100, SE.12.2) no se
corrige, pero se registra una observación `POSIBLE_ERROR_ESCRITURA`. Los demás nombres (`Analitica`, `Area 8`,
`Area 9`) se conservan sin corrección.
**Motivo:** es la corrección que menciona el enunciado (§2) con el menor riesgo; el posible error del nombre queda
visible para revisión sin alterar el dato original.

### D8. `ACTIVO` del Excel frente a la baja lógica del registro — DECIDIDA: opción A con ajuste

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. Dos campos independientes**: `activo_excel` (atributo de negocio S/N/desconocido, editable) y `activo` (baja lógica del registro). Todo importado entra con `activo = true`, incluso SE.05.01 (`N`) | No pierde información; el desconocido no se fuerza; el filtro "estado" puede ofrecer ambos | Dos conceptos de "activo": la interfaz debe rotularlos claramente ("Activo según catálogo" / "Registro dado de baja") |
| **B. Un solo campo**: `activo_excel` determina la baja lógica (`N` → inactivo) | Un solo concepto | No hay forma de mapear "desconocido" sin inventar; SE.05.01 quedaría oculto como si se hubiera borrado; mezcla dato importado con acción administrativa |
| **C. Estado único de tres valores** (`ACTIVO`, `INACTIVO`, `DESCONOCIDO`) que sirve para ambos | Un solo campo sin perder el desconocido | Una baja administrativa sobrescribe el valor original del Excel |

Enunciado §2: E es "indicador S/N; conservar desconocidos"; §3.3 pide "desactivar servicios" y filtrar por
estado.

**Decisión: A con ajustes.** `activo_excel` y `activo` (baja lógica) son campos independientes; todo lo importado
entra con `activo = true`.

- **Ajuste 1 (filtros):** el listado de servicios permite filtrar por ambos campos por separado (ver §3.3,
  "Filtros del listado"), para que servicios como SE.05.01 (`ACTIVO = N`) sean localizables.
- **Ajuste 2 (valor original):** `activo_excel` conserva el texto original del Excel. `S` y `N` se reconocen;
  cualquier otro valor no vacío se guarda tal cual y genera la observación `VALOR_NO_RECONOCIDO`; solo la celda
  vacía se guarda como NULL. La interfaz muestra NULL como "Desconocido" y el filtro ofrece
  S / N / Desconocido / Otros / Todos.

**Motivo:** no se pierde el dato del Excel ni se confunde con una acción administrativa. El enunciado (§2) pide
"conservar los valores desconocidos como tales", y con NULL se perdería un valor original distinto de S/N.

### D9. Garantía de que el usuario responsable pertenece a la sección responsable — DECIDIDA: opción A

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. Validación en servidor**: `ServicioNivel2.clean()` comprueba `usuario.puesto.seccion_id == seccion_responsable_id`, usuario activo y sección activa; toda escritura (formularios, importador, comando demo) pasa por una función de servicio que llama `full_clean()`. Se suma el CHECK `ck_n2_usuario_requiere_seccion` | Mensajes claros; fácil de probar (P11); sin lógica duplicada | Una escritura SQL directa podría saltarla |
| **B. A + trigger PostgreSQL** (`BEFORE INSERT OR UPDATE` en servicio N2 y `BEFORE UPDATE OF puesto_id` en usuario) | Garantía también ante SQL directo | Lógica repetida en `RunSQL`; errores de BD menos legibles; más mantenimiento |
| **C. FK compuesta**: columna `seccion_id` desnormalizada en usuario con FK `(puesto_id, seccion_id)` → puesto, y FK `(usuario_responsable_id, seccion_responsable_id)` → usuario | Garantía declarativa pura | Django 5.2 no soporta FK compuestas (requiere SQL manual); columna redundante que hay que mantener al mover puestos |

**Decisión: A.** Validación en servidor con `clean()` y una función de servicio común (formularios, importador y
comando demo), más el CHECK `ck_n2_usuario_requiere_seccion`. Se rechaza cambiar el puesto de un usuario
responsable a otro de una sección distinta mientras siga asignado, listando los servicios afectados.
**Motivo:** mensajes claros y fácil de probar (P11) sin duplicar lógica en la base; coherente con D1.

---

## 8. Supuestos explícitos

| # | Supuesto | Consecuencia si no se cumple |
|---|---|---|
| S1 | Los códigos se comparan **exactamente** (sin mayúsculas/minúsculas ni recorte) para unicidad; los formularios solo recortan espacios iniciales/finales de lo que escribe el usuario | Si se quiere unicidad insensible a mayúsculas, cambiar a `UNIQUE (lower(codigo))` |
| S2 | Longitudes: códigos `varchar(20)` (el más largo del Excel tiene 8), nombres `varchar(200)` (el más largo ≈ 72) | Ampliar sin pérdida si aparece un dato mayor |
| S3 | `numeric(14,4)` basta para mínimo/máximo (Excel: 1, 100, 12, 24); los floats de openpyxl se convierten con `Decimal(str(v))` | Ajustar precisión |
| S4 | **Aceptado (v2).** Usuario.puesto es obligatorio, también para las cuentas demo; el comando de cuentas demo crea una estructura organizacional mínima de demostración (dato nuevo, no del Excel) | Si se requiere un administrador sin puesto, `puesto_id` pasaría a NULL y habría que justificar la excepción |
| S5 | Se exige correo **y** nombre de usuario, ambos únicos; se puede iniciar sesión con cualquiera | Si solo se usa uno, se elimina el otro |
| S6 | **Aceptado (v2).** No se usa el sitio de administración de Django ni `is_staff`/`is_superuser`; la autorización se basa solo en `rol` | Si se quiere `/admin/`, usar `AbstractUser` y sincronizar `is_staff` con `rol` |
| S7 | **Aceptado (v2).** Al repetir la importación, el importador solo sobrescribe campos procedentes del Excel (A–L); **no** toca `seccion_responsable`, `usuario_responsable`, `activo` ni `estado_revision = 'REVISADO'` puesto por un administrador | Si se prefiere no sobrescribir ninguna edición manual, habría que revisar esta regla |
| S8 | Una baja lógica hecha por un administrador no se revierte al reimportar | Ídem |
| S9 | Las reglas de mapeo se versionan como migración de datos, no se editan desde la interfaz | Si se quieren editar en la interfaz, añadir CRUD solo para administrador |
| S10 | Si los controles 12/46 no coinciden, la ejecución se marca `FALLIDA` y se revierte la transacción | Si se prefiere importar parcialmente, cambiar a observación `ERROR` |
| S11 | Los textos del Excel se guardan sin recortar (incluido I5 `'Revele su rollo '`) y se tratan solo como dato | — |
| S12 | El servicio nivel 1 no tiene atributos E–L propios; todos pertenecen al nivel 2 | — |
