# Fases y contexto entregado al asistente

Registro de qué documentos se proporcionan al asistente de IA en cada fase y por qué. Las fases futuras indican
los documentos **previstos**; se actualizan cuando la fase se ejecute.

| # | Fase | Estado | Documentos entregados al asistente | Por qué |
|---|---|---|---|---|
| 1 | Análisis del Excel | realizada | `docs/contexto/enunciado.md`, `data/CatalogoServicios.xlsx` | Obtener hechos verificables por código (combinaciones, 12/46, SE.12, vacíos, listas) antes de diseñar; el enunciado da los controles esperados |
| 2 | Contexto | realizada | `enunciado.md`, `analisis-excel.md`, `scripts/analizar_excel.py` | Consolidar en `AGENTS.md` alcance, stack, reglas, límites y decisiones pendientes para todas las fases siguientes |
| 3 | Modelo de datos | realizada | `AGENTS.md`, `enunciado.md` (§2, §3, §3.4), `analisis-excel.md` | Diseñar entidades, restricciones de unicidad, jerarquía y campos que conserven todo el Excel, incluidos ausentes y trazabilidad; resultado en `modelo-datos.md` con decisiones D1–D9 tomadas por el usuario (AGENTS.md v2) |
| 4 | Scaffold y Docker | prevista | `AGENTS.md` (§2, §6, §7, §8), `enunciado.md` (§5) | Crear proyecto Django con apps definidas, Compose con PostgreSQL y volumen, `.env.example`, sin instalar nada en el anfitrión |
| 5 | Autenticación | prevista | `AGENTS.md` (§4, §8), `enunciado.md` (§3.1, P01–P03), modelo de datos | Login local, Argon2, roles, sesión invalidada al cerrar, usuarios inactivos bloqueados, cuentas demo sin secretos en Git |
| 6 | Organización | prevista | `AGENTS.md` (§4), `enunciado.md` (§3.2, P04, P05, P11), modelo de datos | CRUD con baja lógica, unicidad dentro del padre, sin huérfanos ni padres inactivos; requiere la política de desactivación decidida |
| 7 | Catálogo | prevista | `AGENTS.md` (§4), `enunciado.md` (§3.3, P09, P10, P11), modelo de datos | Mantenimiento de servicios y catálogos, validación mínimo ≤ máximo, búsqueda/filtros, responsable dentro de la sección |
| 8 | Importación | prevista | `AGENTS.md` (§5, §9), `analisis-excel.md` completo, `enunciado.md` (§3.4, P06–P08), modelo de datos | Importador idempotente con observaciones; requiere decisiones pendientes de §5 (SE.12, SE.12.3, filas 42/67, desconocidos, mapeos) |
| 9 | Pruebas | prevista | `AGENTS.md` (§7, §10), `enunciado.md` (§6), código de las fases 5–8 | Automatizar P01–P12 con datos aislados y crear `scripts/verificar.sh` como definición de terminado |
| 10 | Documentación | prevista | `AGENTS.md`, `enunciado.md` (§4, §7, §8), `docs/prompts/`, `docs/evidencias/`, resultados reales de pruebas | Redactar `README.md` y `docs/RESOLUCION.md` con evidencias reales, sin inventar resultados |
