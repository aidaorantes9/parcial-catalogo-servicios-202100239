#!/usr/bin/env bash
# Verificación completa del proyecto (definición de terminado, AGENTS.md §10).
# Uso: bash scripts/verificar.sh [--completo]
#   --completo  además ejecuta al final la prueba de persistencia P12 (scripts/prueba_persistencia.sh),
#               que reinicia los contenedores con `docker compose down` (sin -v) y `up -d --wait`.
# Requiere .env (cp .env.example .env). Reconstruye y levanta los servicios para verificar el código actual.
set -euo pipefail

completo=0
for argumento in "$@"; do
    case "$argumento" in
        --completo) completo=1 ;;
        *)
            echo "Opción desconocida: $argumento (uso: bash scripts/verificar.sh [--completo])" >&2
            exit 2
            ;;
    esac
done

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$raiz"

mkdir -p docs/evidencias
log="docs/evidencias/verificacion-$(date +%Y%m%d-%H%M).log"
# Si ya hubo una ejecución en el mismo minuto, se agrega un sufijo para no mezclar dos ejecuciones.
n=2
while [ -e "$log" ]; do
    log="docs/evidencias/verificacion-$(date +%Y%m%d-%H%M)-$n.log"
    n=$((n + 1))
done
exec > >(tee "$log") 2>&1

echo "== Verificación $(date '+%Y-%m-%d %H:%M:%S %Z') =="
echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'sin git')"
echo "Log: $log"
[ "$completo" -eq 1 ] && echo "Modo: --completo (incluye persistencia P12)"

paso() {
    local nombre="$1"
    shift
    echo
    echo "---- $nombre ----"
    if "$@"; then
        echo "PASA: $nombre"
    else
        local codigo=$?
        echo "FALLA: $nombre (código $codigo)"
        echo "Verificación detenida en el primer fallo. Log: $log"
        exit 1
    fi
}

web() { docker compose exec -T web "$@"; }

# Revisa los logs de web desde el último arranque del contenedor; falla si hay errores y los muestra.
logs_web_sin_errores() {
    local contenedor inicio encontradas
    contenedor="$(docker compose ps -q web)"
    inicio="$(docker inspect -f '{{.State.StartedAt}}' "$contenedor")"
    echo "Revisando logs de web desde $inicio"
    encontradas="$(docker compose logs --no-color --since "$inicio" web 2>&1 \
        | grep -E '\[ERROR\]|Traceback|CRITICAL' || true)"
    if [ -n "$encontradas" ]; then
        echo "Líneas con errores en los logs de web:"
        echo "$encontradas"
        return 1
    fi
    echo "Sin líneas [ERROR], Traceback ni CRITICAL."
}

paso "docker compose config" docker compose config --quiet
paso "construir y levantar servicios (healthy)" docker compose up --build -d --wait
paso "logs de web sin errores" logs_web_sin_errores
paso "ruff check" web ruff check --no-cache .
paso "ruff format --check" web ruff format --check --no-cache .
paso "migraciones al día (makemigrations --check --dry-run)" \
    web python manage.py makemigrations --check --dry-run
paso "SHA-256 del Excel sin cambios" sha256sum -c data/CatalogoServicios.xlsx.sha256
paso "pytest" web pytest
if [ "$completo" -eq 1 ]; then
    paso "persistencia P12 (down sin -v / up)" bash scripts/prueba_persistencia.sh
fi

echo
echo "== RESULTADO: PASA (todos los pasos) =="
