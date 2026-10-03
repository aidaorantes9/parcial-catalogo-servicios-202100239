"""Funciones de servicio comunes del catálogo (D9).

Toda escritura de un servicio de nivel 2 (formularios, importador y comando de datos demo) pasa por
`guardar_servicio_nivel2`, que ejecuta `full_clean()` antes de guardar. `ServicioNivel2.clean()`
usa `validar_responsables` para que la regla del responsable tenga un solo punto de verdad.
"""

from django.db import transaction


def validar_responsables(
    seccion, usuario, *, verificar_seccion_activa=True, verificar_usuario_activo=True
):
    """Errores por campo de la asignación de responsables; diccionario vacío si es válida.

    - Un usuario responsable exige una sección responsable.
    - El usuario debe pertenecer a esa sección (su puesto está en ella).
    - Solo se asignan secciones y usuarios activos. Los indicadores permiten conservar una
      asignación existente que no cambia (p. ej. al editar un servicio dado de baja).
    """
    errores = {}
    if seccion is not None and verificar_seccion_activa and not seccion.activo:
        errores["seccion_responsable"] = (
            f"La sección «{seccion}» está inactiva; elija una sección activa."
        )
    if usuario is None:
        return errores
    if seccion is None:
        errores["usuario_responsable"] = (
            "No se puede asignar un usuario responsable sin sección responsable. "
            "Elija primero la sección."
        )
        return errores
    if verificar_usuario_activo and not usuario.is_active:
        errores["usuario_responsable"] = (
            f"El usuario «{usuario.username}» está inactivo; elija un usuario activo."
        )
        return errores
    seccion_usuario = usuario.puesto.seccion
    if seccion_usuario.pk != seccion.pk:
        errores["usuario_responsable"] = (
            f"El usuario «{usuario.username}» pertenece a la sección «{seccion_usuario}», no a "
            f"la sección responsable «{seccion}». Elija un usuario de esa sección."
        )
    return errores


@transaction.atomic
def guardar_servicio_nivel2(servicio):
    """Valida con `full_clean()` (incluye D9, mínimo ≤ máximo y referencias activas) y guarda."""
    servicio.full_clean()
    servicio.save()
    return servicio


def asignar_responsables(servicio, seccion, usuario=None):
    """Asigna sección y usuario responsables con las mismas validaciones que el formulario."""
    servicio.seccion_responsable = seccion
    servicio.usuario_responsable = usuario
    return guardar_servicio_nivel2(servicio)
