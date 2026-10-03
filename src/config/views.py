from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
def inicio(request):
    return render(request, "inicio.html")


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
