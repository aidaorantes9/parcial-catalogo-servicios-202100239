from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import (
    password_validators_help_text_html,
    validate_password,
)

from cuentas.models import Rol, Usuario
from organizacion.models import Puesto

MENSAJE_LOGIN_INVALIDO = "Usuario o correo y contraseña no válidos."


class LoginForm(AuthenticationForm):
    """Un único mensaje para usuario inexistente, contraseña incorrecta o cuenta inactiva."""

    username = forms.CharField(
        label="Usuario o correo",
        max_length=254,
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )
    error_messages = {
        "invalid_login": MENSAJE_LOGIN_INVALIDO,
        "inactive": MENSAJE_LOGIN_INVALIDO,
    }


class PuestoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.ruta


class UsuarioBaseForm(forms.ModelForm):
    """Campos comunes de alta y edición. Nunca incluye el hash de contraseña."""

    puesto = PuestoChoiceField(queryset=Puesto.objects.none(), label="Puesto")

    def __init__(self, *args, usuario_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_actual = usuario_actual
        # Solo puestos activos; en edición se conserva el actual aunque se haya desactivado
        # (el modelo rechaza cambiar a un puesto inactivo, no conservarlo).
        activos = Puesto.con_jerarquia().filter(activo=True)
        if self.instance.pk:
            activos = activos | Puesto.con_jerarquia().filter(pk=self.instance.puesto_id)
        self.fields["puesto"].queryset = activos.order_by(
            "seccion__departamento__area__empresa__codigo",
            "seccion__departamento__area__codigo",
            "seccion__departamento__codigo",
            "seccion__codigo",
            "codigo",
        )

    def _existe_otro(self, **filtro):
        return Usuario.objects.filter(**filtro).exclude(pk=self.instance.pk).exists()

    def clean_email(self):
        email = Usuario.objects.normalize_email(self.cleaned_data["email"].strip())
        if self._existe_otro(email__iexact=email):
            raise forms.ValidationError("Ya existe un usuario con ese correo.")
        return email

    def clean_nombre(self):
        return self.cleaned_data["nombre"].strip()

    def clean_rol(self):
        rol = self.cleaned_data["rol"]
        es_uno_mismo = self.usuario_actual and self.instance.pk == self.usuario_actual.pk
        if es_uno_mismo and rol != Rol.ADMIN:
            raise forms.ValidationError("No puede quitarse a sí mismo el rol de administrador.")
        return rol


class UsuarioCrearForm(UsuarioBaseForm):
    password1 = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = Usuario
        fields = ["username", "email", "nombre", "rol", "puesto"]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if self._existe_otro(username__iexact=username):
            raise forms.ValidationError("Ya existe un usuario con ese nombre de usuario.")
        return username

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get("password1"), datos.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return datos

    def _post_clean(self):
        super()._post_clean()
        # Igual que UserCreationForm: se valida con la instancia ya construida (similitud con
        # usuario, correo y nombre).
        password = self.cleaned_data.get("password2")
        if password and not self.has_error("password2"):
            try:
                validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error("password1", error)

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario


class UsuarioEditarForm(UsuarioBaseForm):
    """Edición de nombre, correo, rol y puesto. El nombre de usuario no se modifica."""

    class Meta:
        model = Usuario
        fields = ["nombre", "email", "rol", "puesto"]
