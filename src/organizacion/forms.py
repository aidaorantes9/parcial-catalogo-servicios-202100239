"""Formularios de la jerarquía organizacional.

El estado (activo) no se edita aquí: la baja lógica y la reactivación tienen su propia acción, que
aplica la política D1.
"""

from django import forms
from django.core.exceptions import ValidationError


class PadreChoiceField(forms.ModelChoiceField):
    """Ofrece solo padres activos (y el actual en edición), pero distingue en el mensaje un padre
    inactivo de uno inexistente, también ante peticiones directas sin el formulario."""

    def label_from_instance(self, obj):
        return obj.ruta

    def to_python(self, value):
        try:
            return super().to_python(value)
        except ValidationError:
            modelo = self.queryset.model
            try:
                padre = modelo.objects.filter(pk=value).first()
            except (TypeError, ValueError):
                padre = None
            if padre is not None and not padre.activo:
                raise ValidationError(
                    f"«{padre}» está inactivo; elija un registro activo.",
                    code="padre_inactivo",
                ) from None
            raise ValidationError(
                f"El valor seleccionado para {modelo._meta.verbose_name} no existe.",
                code="padre_inexistente",
            ) from None


class UnidadForm(forms.ModelForm):
    """Base común: código y nombre recortados, padre activo y código único dentro del padre."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        campo_padre = self._meta.model.campo_padre
        if campo_padre:
            modelo_padre = self._meta.model.modelo_padre()
            padres = modelo_padre.con_jerarquia().filter(activo=True)
            actual = getattr(self.instance, f"{campo_padre}_id")
            if actual:
                padres = padres | modelo_padre.con_jerarquia().filter(pk=actual)
            self.fields[campo_padre] = PadreChoiceField(
                queryset=padres.order_by("codigo"),
                label=modelo_padre._meta.verbose_name.capitalize(),
            )

    def clean(self):
        datos = super().clean()
        modelo = self._meta.model
        codigo = datos.get("codigo")
        if not codigo:
            return datos
        filtro = {"codigo": codigo}
        if modelo.campo_padre:
            padre = datos.get(modelo.campo_padre)
            if padre is None:
                return datos  # El error del padre ya se informa en su campo.
            filtro[modelo.campo_padre] = padre
        if modelo.objects.filter(**filtro).exclude(pk=self.instance.pk).exists():
            nombre = modelo._meta.verbose_name
            mensaje = f"El código «{codigo}» ya está en uso por otro registro de {nombre}"
            if modelo.campo_padre:
                mensaje += f" en «{padre}»"
            self.add_error("codigo", mensaje + ".")
        return datos


def formulario_para(modelo):
    campos = ([modelo.campo_padre] if modelo.campo_padre else []) + ["codigo", "nombre"]
    return forms.modelform_factory(modelo, form=UnidadForm, fields=campos)
