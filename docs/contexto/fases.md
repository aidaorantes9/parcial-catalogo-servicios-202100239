# Fases y contexto entregado al asistente

Registro de qué documentos se proporcionan al asistente de IA en cada fase y por qué. Las fases futuras indican
los documentos **previstos**; se actualizan cuando la fase se ejecute.

| # | Fase | Estado | Documentos entregados al asistente | Por qué |
|---|---|---|---|---|
| 1 | Análisis del Excel | realizada | `docs/contexto/enunciado.md`, `data/CatalogoServicios.xlsx` | Obtener hechos verificables por código (combinaciones, 12/46, SE.12, vacíos, listas) antes de diseñar; el enunciado da los controles esperados |
| 2 | Contexto | realizada | `enunciado.md`, `analisis-excel.md`, `scripts/analizar_excel.py` | Consolidar en `AGENTS.md` alcance, stack, reglas, límites y decisiones pendientes para todas las fases siguientes |
| 3 | Modelo de datos | realizada | `AGENTS.md`, `enunciado.md` (§2, §3, §3.4), `analisis-excel.md` | Diseñar entidades, restricciones de unicidad, jerarquía y campos que conserven todo el Excel, incluidos ausentes y trazabilidad; resultado en `modelo-datos.md` con decisiones D1–D9 tomadas por el usuario (AGENTS.md v2) |
| 4 | Scaffold y Docker | realizada (prompt 05) | Sesión limpia: solo `AGENTS.md` (vía `CLAUDE.md`) y `modelo-datos.md` | Comprobar que el contexto versionado bastaba sin historial del chat; crear Django con las cuatro apps, Compose con PostgreSQL y volumen, `.env.example` y los scripts `verificar.sh`, `pruebas.sh` y `reiniciar_datos_prueba.sh`. El contexto (S6) permitió detectar un error del prompt (`AbstractUser` frente a `AbstractBaseUser`) |
| 5 | Autenticación | realizada (prompt 06) | `AGENTS.md`, `modelo-datos.md`, `enunciado.md` (§3.1, §3.2) | Login local con Argon2, roles validados en el servidor, logout que invalida la sesión, inactivos bloqueados y `crear_cuentas_demo`; se adelantaron los modelos de organización porque las cuentas demo necesitan un puesto. Resultado: `seguridad.md` nuevo |
| 6 | Organización | realizada (prompt 07) | `AGENTS.md`, `modelo-datos.md` (organización, D1, supuestos), `seguridad.md`, `enunciado.md` (§3.2) | CRUD con baja lógica, unicidad dentro del padre, sin huérfanos ni padres inactivos y rechazo con lista de dependientes (D1), reutilizando permisos y plantillas existentes |
| 7 | Catálogo | realizada (prompt 08) | `AGENTS.md`, `modelo-datos.md` (catálogos, servicios, trazabilidad, D1, D6–D9), `seguridad.md`, `enunciado.md` (§3.3) | Catálogos, servicios N1/N2, mínimo ≤ máximo, búsqueda/filtros/ficha y responsable dentro de la sección; se crearon las tablas de trazabilidad sin el importador |
| 8 | Importación | realizada (prompt 09) | `AGENTS.md` (§5, §9), `analisis-excel.md`, `modelo-datos.md` (importación, trazabilidad, claves naturales, D2–D8), `enunciado.md` (§3.4), `scripts/analizar_excel.py` | Importador idempotente con observaciones y `cargar_demo`. Resultado: `mapeo-excel.md` nuevo y `AGENTS.md` v3 con las reglas que aparecieron al implementarlo |
| 9 | Pruebas | prevista | `AGENTS.md` (§7, §10), `enunciado.md` (§6), código de las fases 5–8 | Automatizar P01–P12 con datos aislados y crear `scripts/verificar.sh` como definición de terminado |
| 10 | Documentación | prevista | `AGENTS.md`, `enunciado.md` (§4, §7, §8), `docs/prompts/`, `docs/evidencias/`, resultados reales de pruebas | Redactar `README.md` y `docs/RESOLUCION.md` con evidencias reales, sin inventar resultados |
