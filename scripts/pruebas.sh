#!/usr/bin/env bash
# Ejecuta pytest dentro del contenedor web con salida detallada.
# Uso: bash scripts/pruebas.sh [argumentos de pytest]   (ej.: bash scripts/pruebas.sh -m p01)
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

opciones_exec=()
[ -t 1 ] || opciones_exec+=(-T)

docker compose exec "${opciones_exec[@]}" web pytest -v "$@"
