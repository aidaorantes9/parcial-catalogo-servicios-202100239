#!/usr/bin/env bash
# Ejecuta pytest dentro del contenedor web con salida detallada.
# Uso: bash scripts/pruebas.sh [argumentos de pytest]
#   bash scripts/pruebas.sh                 todas las pruebas
#   bash scripts/pruebas.sh -m p06          un escenario por su marcador (p01 … p11)
#   bash scripts/pruebas.sh -m "p06 or p07" varios escenarios
#   bash scripts/pruebas.sh -m importacion  marcadores extra: humo, catalogo, importacion, demo
#   bash scripts/pruebas.sh -m p12          P12 no es una prueba de pytest: delega en
#                                           scripts/prueba_persistencia.sh (base de evaluación)
# Matriz de escenarios y comandos: docs/contexto/matriz-pruebas.md
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "$#" -eq 2 ] && [ "$1" = "-m" ] && [ "$2" = "p12" ]; then
    echo "P12 reinicia los contenedores (down sin -v / up) sobre la base de evaluación:"
    echo "se ejecuta bash scripts/prueba_persistencia.sh"
    exec bash scripts/prueba_persistencia.sh
fi

opciones_exec=()
[ -t 1 ] || opciones_exec+=(-T)

docker compose exec "${opciones_exec[@]}" web pytest -v "$@"
