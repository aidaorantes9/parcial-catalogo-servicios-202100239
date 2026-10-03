"""Jerarquía DEMO mínima, compartida por `crear_cuentas_demo` y `cargar_demo`.

Son datos nuevos de demostración (`es_demo=True`), nunca provenientes del Excel.
"""

from organizacion.models import Area, Departamento, Empresa, Puesto, Seccion

CODIGO_DEMO = "DEMO"

# (modelo, campo padre, nombre).
JERARQUIA_DEMO = [
    (Empresa, None, "Empresa de demostración"),
    (Area, "empresa", "Área de demostración"),
    (Departamento, "area", "Departamento de demostración"),
    (Seccion, "departamento", "Sección de demostración"),
    (Puesto, "seccion", "Puesto de demostración"),
]


def asegurar_jerarquia_demo(guardar, escribir):
    """Crea, si no existen, los niveles DEMO y devuelve el puesto DEMO.

    `guardar(registro)` valida y guarda; `escribir(texto)` informa lo creado.
    """
    padre = None
    for modelo, campo_padre, nombre in JERARQUIA_DEMO:
        filtro = {"codigo": CODIGO_DEMO}
        if campo_padre:
            filtro[campo_padre] = padre
        registro = modelo.objects.filter(**filtro).first()
        if registro is None:
            registro = modelo(**filtro, nombre=nombre, es_demo=True)
            guardar(registro)
            escribir(f"Creado {modelo._meta.verbose_name}: {registro}")
        padre = registro
    return padre
