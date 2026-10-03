"""Presentación de datos ausentes: NULL se muestra como texto, nunca como 0 ni vacío (D6)."""

from decimal import Decimal

from django import template

register = template.Library()

SIN_DATO = "Sin dato"


@register.filter
def sin_dato(valor, texto=SIN_DATO):
    """«Sin dato» (o el texto indicado) si el valor es NULL; un 0 o un False se muestran."""
    return texto if valor is None else valor


@register.filter
def numero(valor):
    """Decimal sin ceros de relleno (1.0000 → 1, 0 → 0); NULL → «Sin dato»."""
    if valor is None:
        return SIN_DATO
    if isinstance(valor, Decimal):
        return f"{valor.normalize():f}"
    return valor
