#!/usr/bin/env bash
# REINICIO DESTRUCTIVO: detiene los servicios y BORRA el volumen de PostgreSQL (docker compose down -v).
# Es el único script autorizado a usar `down -v` (AGENTS.md §8.3). Requiere confirmación explícita.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "ADVERTENCIA: se eliminarán los contenedores y el volumen de la base de datos."
echo "Se PIERDEN todos los datos: usuarios, organización, catálogo importado y asignaciones."
echo "Esta acción no se puede deshacer."
read -r -p 'Escriba BORRAR para confirmar: ' confirmacion

if [ "$confirmacion" != "BORRAR" ]; then
    echo "Cancelado: no se borró nada."
    exit 1
fi

docker compose down -v
echo "Datos eliminados. Para levantar de nuevo: docker compose up --build -d"
