# Catálogo de servicios de TI

Aplicación web que sistematiza el catálogo de `data/CatalogoServicios.xlsx`, con usuarios, roles y estructura organizacional. Está hecha con Django 5.2 y PostgreSQL 16 y todo se ejecuta en Docker. La explicación completa de cómo resolví el parcial está en [docs/RESOLUCION.md](docs/RESOLUCION.md).

**Integrante:** Aída Alejandra Mansilla Orantes, carné 202100239

## Requisitos

- Git y Docker con Docker Compose v2. No hace falta instalar Python ni PostgreSQL.
- Lo probé con Docker 29.1.3 y Docker Compose 2.40.3 en Linux Mint 22.3.

## 1. Clonar y configurar

```bash
git clone https://github.com/aidaorantes9/parcial-catalogo-servicios-202100239.git
cd parcial-catalogo-servicios-202100239
git checkout parcial-v2.0
cp .env.example .env
```

`.env.example` trae valores de demostración que sirven tal cual para evaluar.

## 2. Levantar y cargar datos

```bash
docker compose up --build -d --wait
bash scripts/importar.sh
docker compose exec web python manage.py crear_cuentas_demo
docker compose exec web python manage.py cargar_demo
```

- Las migraciones se aplican solas al arrancar el contenedor `web`.
- `importar.sh` debe terminar con 12 códigos de nivel 1 y 46 de nivel 2 en PASA. Si se repite, da 0 creados y no duplica nada.
- `cargar_demo` crea la organización de demostración y 4 asignaciones de responsables.

## 3. Usar la aplicación

- URL: http://127.0.0.1:8000 (el puerto 8000 está publicado solo en 127.0.0.1).
- Administrador: usuario y contraseña de las variables `DEMO_ADMIN_*` de `.env`.
- Consulta: usuario y contraseña de las variables `DEMO_CONSULTA_*` de `.env`.

## 4. Pruebas

```bash
bash scripts/verificar.sh
bash scripts/verificar.sh --completo
bash scripts/pruebas.sh -m p06
```

- `verificar.sh` revisa la configuración, los logs, el lint, las migraciones, el hash del Excel y ejecuta pytest (P01 a P11). Termina con código 0 si todo pasa.
- `--completo` agrega la prueba de persistencia P12, que reinicia los contenedores sin borrar el volumen.
- `pruebas.sh -m pNN` ejecuta un solo escenario.
- Pytest usa una base aislada (`test_*`), así que no toca los datos de evaluación. El detalle está en [docs/contexto/matriz-pruebas.md](docs/contexto/matriz-pruebas.md).

## 5. Operación

| Acción | Comando |
|---|---|
| Ver estado | `docker compose ps` |
| Ver logs | `docker compose logs -f web` |
| Detener sin perder datos | `docker compose down` |
| Volver a levantar | `docker compose up -d --wait` |

### Reinicio destructivo

Solo para empezar de cero con datos de prueba. Borra la base de datos y pide escribir `BORRAR` para confirmar:

```bash
bash scripts/reiniciar_datos_prueba.sh
```

Después hay que repetir el paso 2.

## Documentación

- [docs/RESOLUCION.md](docs/RESOLUCION.md): solución, decisiones, matriz de requisitos y resultados.
- [AGENTS.md](AGENTS.md): contexto del proyecto para el asistente de IA.
- [docs/prompts/](docs/prompts/) y [docs/evidencias/](docs/evidencias/): prompts usados y evidencias.
