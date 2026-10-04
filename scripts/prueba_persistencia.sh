#!/usr/bin/env bash
# P12: reiniciar los contenedores sin eliminar volúmenes → persisten los datos registrados.
# Uso: bash scripts/prueba_persistencia.sh
#
# Trabaja sobre la base de evaluación (no sobre la base test_* de pytest) y no borra nada:
#   1. Exige servicios levantados (db y web healthy) y el catálogo importado.
#   2. Registra conteos: servicios N1 y N2, usuarios, empresas, asignaciones y ejecuciones.
#   3. Crea una empresa marcador P12-AAAAMMDDHHMMSS (dato de prueba, nombre explícito).
#   4. docker compose down (SIN -v) y docker compose up -d --wait.
#   5. Comprueba el marcador, los conteos (antes + marcador) y el volumen; da de baja el marcador
#      (baja lógica: queda inactivo, no se elimina).
# Imprime PASA/FALLA por comprobación; sale 0 si todo pasa y 1 si algo falla.
# Log: docs/evidencias/persistencia-AAAAMMDD-HHMM.log (con sufijo -2, -3… si ya existe).
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$raiz"

mkdir -p docs/evidencias
log="docs/evidencias/persistencia-$(date +%Y%m%d-%H%M).log"
n=2
while [ -e "$log" ]; do
    log="docs/evidencias/persistencia-$(date +%Y%m%d-%H%M)-$n.log"
    n=$((n + 1))
done
exec > >(tee "$log") 2>&1

echo "== P12 Persistencia $(date '+%Y-%m-%d %H:%M:%S %Z') =="
echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'sin git')"
echo "Log: $log"

fallos=0
comprobar() {
    # comprobar "descripción" condición-como-comando...
    local nombre="$1"
    shift
    if "$@"; then
        echo "PASA: $nombre"
    else
        echo "FALLA: $nombre"
        fallos=$((fallos + 1))
    fi
}

abortar() {
    echo "FALLA: $1"
    echo
    echo "== RESULTADO P12: FALLA (precondición no cumplida) =="
    exit 1
}

# Ejecuta código Python en el contexto de Django dentro de web; imprime solo la línea «P12=…».
django() {
    docker compose exec -T web python manage.py shell --no-imports -c "$1" | sed -n 's/^P12=//p'
}

# Estado de la base de evaluación en una sola línea «clave=valor …».
CONTEOS='
from catalogo.models import ServicioNivel1, ServicioNivel2
from cuentas.models import Usuario
from importacion.models import Ejecucion
from organizacion.models import Empresa
conteos = {
    "n1": ServicioNivel1.objects.count(),
    "n2": ServicioNivel2.objects.count(),
    "n1_importados": ServicioNivel1.objects.filter(origen__isnull=False).count(),
    "n2_importados": ServicioNivel2.objects.filter(origen__isnull=False).count(),
    "usuarios": Usuario.objects.count(),
    "empresas": Empresa.objects.count(),
    "asignaciones": ServicioNivel2.objects.filter(seccion_responsable__isnull=False).count(),
    "ejecuciones": Ejecucion.objects.count(),
    "ejecuciones_exitosas": Ejecucion.objects.filter(estado="EXITOSA").count(),
}
print("P12=" + " ".join(f"{k}={v}" for k, v in conteos.items()))
'

valor() { # valor "clave" "linea de conteos"
    tr ' ' '\n' <<<"$2" | sed -n "s/^$1=//p"
}

estado_servicio() {
    docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q "$1")" 2>/dev/null || echo "ausente"
}

volumen() {
    docker volume ls -q --filter "label=com.docker.compose.project=catalogo-servicios" \
        --filter "label=com.docker.compose.volume=datos_postgres" | head -n 1
}

# ---------------------------------------------------------------- 1. Precondiciones
echo
echo "---- Precondiciones ----"
for servicio in db web; do
    [ "$(estado_servicio "$servicio")" = "healthy" ] \
        || abortar "el servicio $servicio no está levantado y healthy (ejecute: docker compose up -d --wait)"
done
echo "PASA: db y web levantados y healthy"

antes="$(django "$CONTEOS")" || true
[ -n "$antes" ] || abortar "no se pudieron leer los conteos de la base de evaluación"
if [ "$(valor n1_importados "$antes")" -lt 12 ] || [ "$(valor n2_importados "$antes")" -lt 46 ] \
    || [ "$(valor ejecuciones_exitosas "$antes")" -lt 1 ]; then
    abortar "el catálogo no está importado (ejecute: bash scripts/importar.sh)"
fi
echo "PASA: catálogo importado (≥12 N1 y ≥46 N2 con origen, al menos una ejecución EXITOSA)"

vol_nombre="$(volumen)"
[ -n "$vol_nombre" ] || abortar "no se encontró el volumen datos_postgres del proyecto"
vol_creado="$(docker volume inspect -f '{{.CreatedAt}}' "$vol_nombre")"

# ---------------------------------------------------------------- 2. Estado antes
echo
echo "---- Estado antes del reinicio ----"
echo "$antes" | tr ' ' '\n' | sed 's/^/  /'
echo "  volumen=$vol_nombre (creado $vol_creado)"

# ---------------------------------------------------------------- 3. Marcador
codigo="P12-$(date +%Y%m%d%H%M%S)"
echo
echo "---- Marcador ----"
creado="$(django "
from organizacion.models import Empresa
empresa = Empresa(codigo='$codigo', nombre='Dato de prueba P12 (persistencia) — no usar')
empresa.full_clean()
empresa.save()
print(f'P12={empresa.pk}')
")" || true
[ -n "$creado" ] || abortar "no se pudo crear la empresa marcador $codigo"
echo "PASA: empresa marcador $codigo creada (id $creado)"

# ---------------------------------------------------------------- 4. Reinicio sin -v
echo
echo "---- docker compose down (sin -v) ----"
docker compose down
echo
echo "---- docker compose up -d --wait ----"
if ! docker compose up -d --wait; then
    echo "FALLA: los servicios no volvieron a quedar healthy"
    echo
    echo "== RESULTADO P12: FALLA =="
    exit 1
fi
echo "PASA: servicios levantados de nuevo y healthy"

# ---------------------------------------------------------------- 5. Comprobaciones
echo
echo "---- Comprobaciones después del reinicio ----"
despues="$(django "$CONTEOS")" || true
echo "$despues" | tr ' ' '\n' | sed 's/^/  /'

comprobar "mismo volumen datos_postgres (no se recreó)" \
    test "$(volumen)" = "$vol_nombre" -a \
    "$(docker volume inspect -f '{{.CreatedAt}}' "$vol_nombre" 2>/dev/null)" = "$vol_creado"

marcador="$(django "
from organizacion.models import Empresa
e = Empresa.objects.filter(codigo='$codigo').first()
print('P12=' + (f'{e.pk}:{e.activo}' if e else 'NO_EXISTE'))
")" || true
comprobar "el marcador $codigo existe tras el reinicio" test "$marcador" = "$creado:True"

for clave in n1 n2 usuarios asignaciones ejecuciones; do
    a="$(valor "$clave" "$antes")"
    d="$(valor "$clave" "$despues")"
    comprobar "conteo $clave igual ($a → $d)" test "$a" = "$d"
done
a="$(valor empresas "$antes")"
d="$(valor empresas "$despues")"
comprobar "conteo empresas = antes + marcador ($a + 1 → $d)" test "$((a + 1))" = "$d"

# Baja lógica del marcador (no se elimina).
baja="$(django "
from organizacion.models import Empresa
e = Empresa.objects.get(codigo='$codigo')
e.activo = False
e.full_clean()
e.save()
e.refresh_from_db()
print(f'P12={e.activo}')
")" || true
comprobar "marcador $codigo dado de baja (activo = False, registro conservado)" test "$baja" = "False"

echo
if [ "$fallos" -eq 0 ]; then
    echo "== RESULTADO P12: PASA (todas las comprobaciones) =="
    exit 0
fi
echo "== RESULTADO P12: FALLA ($fallos comprobaciones) =="
exit 1
