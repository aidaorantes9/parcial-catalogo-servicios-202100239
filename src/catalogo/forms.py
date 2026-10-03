"""Formularios del catálogo.

- Los selects solo ofrecen opciones activas (y la actual en edición, para no perderla). Un valor
  inactivo o inexistente enviado por petición directa se rechaza con mensaje propio.
- Un campo vacío se guarda como NULL, nunca como 0 ni cadena vacía (D6).
- El estado (activo) no se edita aquí: la baja lógica tiene su propia acción con la política D1.
- Las reglas de negocio (D9, mínimo ≤ máximo, referencias activas) están en `clean()` del
  modelo, que el formulario ejecuta; el guardado pasa por
  `catalogo.servicios.guardar_servicio_nivel2`.
"""

import re

from django import forms

from catalogo.models import ACTIVO_EXCEL_RECONOCIDOS, ServicioNivel1, ServicioNivel2
from catalogo.servicios import guardar_servicio_nivel2
from cuentas.models import Usuario
from organizacion.forms import PadreChoiceField
from organizacion.models import Seccion

# Valor del formulario que representa NULL (desconocido) en ACTIVO del Excel.
ACTIVO_EXCEL_DESCONOCIDO = ""


class OpcionActivaChoiceField(PadreChoiceField):
    """Select de opciones controladas: rechaza inexistentes e inactivas con mensaje distinto."""

    def label_from_instance(self, obj):
        return str(obj)


class SeccionChoiceField(PadreChoiceField):
    def label_from_instance(self, obj):
        return obj.ruta


class UsuarioResponsableChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.username} — {obj.nombre} (sección {obj.puesto.seccion.codigo})"

    def to_python(self, value):
        try:
            return super().to_python(value)
        except forms.ValidationError:
            try:
                usuario = Usuario.objects.filter(pk=value).first()
            except (TypeError, ValueError):
                usuario = None
            if usuario is not None and not usuario.is_active:
                raise forms.ValidationError(
                    f"El usuario «{usuario.username}» está inactivo; elija un usuario activo.",
                    code="usuario_inactivo",
                ) from None
            raise forms.ValidationError(
                "El usuario seleccionado no existe.", code="usuario_inexistente"
            ) from None


def _activos_y_actual(modelo, actual_id, consulta=None):
    consulta = consulta if consulta is not None else modelo.objects.all()
    filtro = consulta.filter(activo=True)
    if actual_id:
        filtro = filtro | consulta.filter(pk=actual_id)
    return filtro


def _texto_o_nulo(valor):
    """NULL si el texto está vacío o solo tiene espacios; si no, se conserva tal cual."""
    if valor is None or not valor.strip():
        return None
    return valor


class CodigoUnicoMixin:
    """Mensaje de código duplicado que incluye el código (igual que en organización)."""

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip()
        modelo = self._meta.model
        if modelo.objects.filter(codigo=codigo).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(
                f"El código «{codigo}» ya está en uso por otro registro de "
                f"{modelo._meta.verbose_name}."
            )
        return codigo

    def clean_nombre(self):
        return self.cleaned_data["nombre"].strip()


class ValorCatalogoCrearForm(forms.ModelForm):
    """Alta de clase, criticidad o tipo. La etiqueta escrita queda como original y mostrada."""

    etiqueta = forms.CharField(label="Etiqueta", max_length=100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        modelo = self._meta.model
        self.fields["codigo"].help_text = "Mayúsculas, dígitos y guion bajo (p. ej. A_DEMANDA)."
        if not self.is_bound:
            ultimo = modelo.objects.order_by("-orden").values_list("orden", flat=True).first()
            self.initial.setdefault("orden", 0 if ultimo is None else ultimo + 1)

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip()
        if not re.fullmatch(r"[A-Z0-9_]+", codigo):
            raise forms.ValidationError(
                "El código solo admite letras mayúsculas sin tildes, dígitos y guion bajo."
            )
        if self._meta.model.objects.filter(codigo=codigo).exists():
            raise forms.ValidationError(f"El código «{codigo}» ya está en uso en este catálogo.")
        return codigo

    def clean_etiqueta(self):
        etiqueta = self.cleaned_data["etiqueta"].strip()
        modelo = self._meta.model
        if (
            modelo.objects.filter(etiqueta_original=etiqueta).exists()
            or modelo.objects.filter(etiqueta_mostrada=etiqueta).exists()
        ):
            raise forms.ValidationError(f"La etiqueta «{etiqueta}» ya existe en este catálogo.")
        return etiqueta

    def _post_clean(self):
        etiqueta = self.cleaned_data.get("etiqueta")
        if etiqueta:
            self.instance.etiqueta_original = etiqueta
            self.instance.etiqueta_mostrada = etiqueta
        super()._post_clean()


class ValorCatalogoEditarForm(forms.ModelForm):
    """Edición: el código y la etiqueta original no cambian. En valores importados del Excel la
    etiqueta mostrada tampoco: solo cambia mediante el mapeo de correcciones (D7)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.importado:
            del self.fields["etiqueta_mostrada"]

    def clean_etiqueta_mostrada(self):
        etiqueta = self.cleaned_data["etiqueta_mostrada"].strip()
        otros = self._meta.model.objects.exclude(pk=self.instance.pk)
        if otros.filter(etiqueta_mostrada=etiqueta).exists():
            raise forms.ValidationError(f"La etiqueta «{etiqueta}» ya existe en este catálogo.")
        return etiqueta


def formularios_valor(modelo):
    """(formulario de alta, formulario de edición) para un catálogo de atributos."""
    crear = forms.modelform_factory(modelo, form=ValorCatalogoCrearForm, fields=["codigo", "orden"])
    editar = forms.modelform_factory(
        modelo, form=ValorCatalogoEditarForm, fields=["etiqueta_mostrada", "orden"]
    )
    return crear, editar


class ServicioNivel1Form(CodigoUnicoMixin, forms.ModelForm):
    class Meta:
        model = ServicioNivel1
        fields = ["codigo", "nombre", "estado_revision"]


class ServicioNivel2Form(CodigoUnicoMixin, forms.ModelForm):
    activo_excel = forms.ChoiceField(
        label="ACTIVO (Excel)",
        required=False,
        help_text="Indicador S/N de la columna ACTIVO del Excel. Es independiente de la baja "
        "lógica del registro.",
    )
    descripcion = forms.CharField(
        label="Descripción", required=False, strip=False, widget=forms.Textarea(attrs={"rows": 3})
    )
    metrica = forms.CharField(label="Métrica", required=False, strip=False, max_length=200)

    class Meta:
        model = ServicioNivel2
        fields = [
            "nivel1",
            "codigo",
            "nombre",
            "activo_excel",
            "clase",
            "criticidad",
            "tipo",
            "descripcion",
            "metrica",
            "minimo",
            "maximo",
            "estado_revision",
            "seccion_responsable",
            "usuario_responsable",
        ]
        help_texts = {
            "minimo": "Vacío si no se conoce (no se guarda como 0).",
            "maximo": "Vacío si no se conoce. Si hay mínimo y máximo, mínimo ≤ máximo.",
            "usuario_responsable": "Opcional. Debe pertenecer a la sección responsable.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instancia = self.instance
        for campo in ServicioNivel2.REFERENCIAS:
            modelo = ServicioNivel2._meta.get_field(campo).related_model
            actual = getattr(instancia, f"{campo}_id")
            original = self.fields[campo]
            self.fields[campo] = OpcionActivaChoiceField(
                queryset=_activos_y_actual(modelo, actual),
                required=original.required,
                label=original.label,
                empty_label="Sin dato" if not original.required else "---------",
            )

        self.fields["seccion_responsable"] = SeccionChoiceField(
            queryset=_activos_y_actual(
                Seccion, instancia.seccion_responsable_id, Seccion.con_jerarquia()
            ).order_by("departamento__area__empresa__codigo", "codigo"),
            required=False,
            label="Sección responsable",
            empty_label="Sin asignar",
        )
        usuarios = Usuario.objects.select_related("puesto__seccion").filter(is_active=True)
        if instancia.usuario_responsable_id:
            usuarios = usuarios | Usuario.objects.select_related("puesto__seccion").filter(
                pk=instancia.usuario_responsable_id
            )
        self.fields["usuario_responsable"] = UsuarioResponsableChoiceField(
            queryset=usuarios.order_by("username"),
            required=False,
            label="Usuario responsable",
            empty_label="Sin asignar",
            help_text=self._meta.help_texts["usuario_responsable"],
        )

        opciones = [(v, v) for v in ACTIVO_EXCEL_RECONOCIDOS]
        opciones.append((ACTIVO_EXCEL_DESCONOCIDO, "Desconocido"))
        if not instancia.activo_excel_reconocido:
            # Un valor original no reconocido se muestra y se conserva salvo que se cambie (D8).
            valor = instancia.activo_excel
            opciones.insert(0, (valor, f"{valor!r} (valor original no reconocido)"))
        self.fields["activo_excel"].choices = opciones
        if not self.is_bound:
            self.initial["activo_excel"] = instancia.activo_excel or ACTIVO_EXCEL_DESCONOCIDO

    def clean_activo_excel(self):
        valor = self.cleaned_data["activo_excel"]
        return None if valor == ACTIVO_EXCEL_DESCONOCIDO else valor

    def clean_descripcion(self):
        return _texto_o_nulo(self.cleaned_data["descripcion"])

    def clean_metrica(self):
        return _texto_o_nulo(self.cleaned_data["metrica"])

    def save(self, commit=True):
        servicio = super().save(commit=False)
        if commit:
            guardar_servicio_nivel2(servicio)
        return servicio
