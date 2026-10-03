from django.contrib.auth.decorators import login_not_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from cuentas.models import Usuario
from organizacion.models import Area, Departamento, Empresa, Puesto, Seccion


@require_GET
def inicio(request):
    """Página de inicio con conteos de registros activos (ambos roles)."""
    conteos = [
        (
            modelo._meta.verbose_name_plural.capitalize(),
            modelo.objects.filter(activo=True).count(),
            f"organizacion:{modelo._meta.model_name}_lista",
        )
        for modelo in (Empresa, Area, Departamento, Seccion, Puesto)
    ]
    conteos.append(
        ("Usuarios", Usuario.objects.filter(is_active=True).count(), "cuentas:usuario_lista")
    )
    return render(request, "inicio.html", {"conteos": conteos})


@login_not_required
@never_cache
@require_GET
def salud(request):
    """Healthcheck: 200 si la aplicación responde y la base de datos acepta consultas."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"estado": "error", "base_datos": "sin conexión"}, status=503)
    return JsonResponse({"estado": "ok"})
