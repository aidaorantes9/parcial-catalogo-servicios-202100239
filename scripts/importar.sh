#!/usr/bin/env bash
# Importa el catálogo desde data/CatalogoServicios.xlsx dentro del contenedor web y guarda la salida.
# Uso: bash scripts/importar.sh [--dry-run] [otros argumentos de importar_catalogo]
# Log: docs/evidencias/importacion-AAAAMMDD-HHMM.log (con sufijo -2, -3… si ya existe).
# Sale con el código del comando: distinto de 0 si aborta o si los controles 12/46 no pasan.
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$raiz"

mkdir -p docs/evidencias
log="docs/evidencias/importacion-$(date +%Y%m%d-%H%M).log"
n=2
while [ -e "$log" ]; do
    log="docs/evidencias/importacion-$(date +%Y%m%d-%H%M)-$n.log"
    n=$((n + 1))
done
exec > >(tee "$log") 2>&1

echo "== Importación $(date '+%Y-%m-%d %H:%M:%S %Z') =="
echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'sin git')"
echo "Log: $log"
echo "Argumentos: ${*:-(ninguno)}"
sha256sum -c data/CatalogoServicios.xlsx.sha256
echo

codigo=0
docker compose exec -T web python manage.py importar_catalogo "$@" || codigo=$?

echo
echo "Código de salida: $codigo"
exit "$codigo"
