"""Catálogo de servicios: catálogos de atributos (clase, criticidad, tipo) y servicios N1 y N2.

Reglas (AGENTS.md §4, modelo-datos.md §3.2 y §3.3):
- Código único en su entidad; baja lógica con `activo`; sin borrado físico (FK PROTECT).
- Los catálogos son opciones controladas: se alimentan solo de las listas E112:H122 (importador) o
  del mantenimiento de un administrador.
- Un dato ausente es NULL, nunca 0 ni cadena vacía (D6). `activo_excel` conserva el texto original
  de la columna E y es independiente de la baja lógica `activo` (D8).
- `minimo <= maximo` cuando ambos existen, en `clean()` y con CHECK en la base.
- El usuario responsable pertenece a la sección responsable (D9, `catalogo.servicios`).
- Desactivar con dependientes activos se rechaza y se listan los dependientes (D1).
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from catalogo.servicios import validar_responsables


class EstadoRevision(models.TextChoices):
    SIN_OBSERVACIONES = "SIN_OBSERVACIONES", "Sin observaciones"
    PENDIENTE_REVISION = "PENDIENTE_REVISION", "Pendiente de revisión"
    REVISADO = "REVISADO", "Revisado"


# Valores de la columna E (ACTIVO) que se reconocen; cualquier otro texto se conserva tal cual.
ACTIVO_EXCEL_RECONOCIDOS = ("S", "N")


def _ck_no_vacio(campo, tabla):
    return models.CheckConstraint(
        condition=~models.Q(**{f"{campo}__regex": r"^\s*$"}),
        name=f"ck_{tabla}_{campo}_no_vacio",
    )


def _ck_estado_revision(tabla):
    return models.CheckConstraint(
        condition=models.Q(estado_revision__in=EstadoRevision.values),
        name=f"ck_{tabla}_estado_revision",
    )


class RegistroCatalogo(models.Model):
    """Baja lógica, auditoría y política D1 comunes a todas las entidades del catálogo."""

    activo = models.BooleanField("activo", default=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        abstract = True

    @classmethod
    def from_db(cls, db, field_names, values):
        instancia = super().from_db(db, field_names, values)
        # Valores leídos de la base, para distinguir altas, cambios y reactivaciones.
        instancia._original = dict(zip(field_names, values, strict=True))
        return instancia

    def _original_de(self, campo):
        return getattr(self, "_original", {}).get(campo)

    def _cambia(self, campo):
        return self._state.adding or getattr(self, campo) != self._original_de(campo)

    def _se_reactiva(self):
        return not self._state.adding and self.activo and self._original_de("activo") is False

    def dependientes_activos(self):
        """Registros activos que impiden la baja lógica (D1)."""
        return []

    def clean(self):
        super().clean()
        if self._state.adding or self.activo or self._original_de("activo") is not True:
            return
        dependientes = self.dependientes_activos()
        if dependientes:
            lista = ", ".join(str(d) for d in dependientes)
            raise ValidationError(
                f"No se puede desactivar «{self}»: tiene dependientes activos ({lista}). "
                "Desactívelos o reasígnelos primero."
            )


class ValorCatalogo(RegistroCatalogo):
    """Forma común de clase, criticidad y tipo de servicio (modelo-datos.md §3.2)."""

    codigo = models.CharField(
        "código",
        max_length=30,
        unique=True,
        error_messages={"unique": "Ya existe un valor con ese código en este catálogo."},
    )
    etiqueta_original = models.CharField(
        "etiqueta original",
        max_length=100,
        unique=True,
        error_messages={"unique": "Ya existe un valor con esa etiqueta en este catálogo."},
        help_text="Texto exacto de la lista del Excel o el registrado al crear el valor.",
    )
    etiqueta_mostrada = models.CharField("etiqueta", max_length=100)
    # Agregado por diseño: orden de la lista del Excel (en criticidad, la escala).
    orden = models.PositiveSmallIntegerField("orden")
    # Agregado por diseño: fila de E112:H122 de donde proviene; NULL si se creó en la aplicación.
    fila_origen = models.PositiveIntegerField("fila de origen", null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["orden", "codigo"]

    def __str__(self):
        return self.etiqueta_mostrada

    @property
    def importado(self):
        return self.fila_origen is not None

    @property
    def corregido(self):
        return self.etiqueta_mostrada != self.etiqueta_original

    def dependientes_activos(self):
        if not self.pk:
            return []
        return list(self.servicios.filter(activo=True).order_by("codigo"))

    @classmethod
    def restricciones(cls, tabla):
        return [
            models.CheckConstraint(
                condition=models.Q(codigo__regex=r"^[A-Z0-9_]+$"), name=f"ck_{tabla}_codigo"
            ),
            _ck_no_vacio("etiqueta_original", tabla),
            _ck_no_vacio("etiqueta_mostrada", tabla),
        ]


class ClaseServicio(ValorCatalogo):
    class Meta(ValorCatalogo.Meta):
        verbose_name = "clase de servicio"
        verbose_name_plural = "clases de servicio"
        constraints = ValorCatalogo.restricciones("catalogo_claseservicio")


class Criticidad(ValorCatalogo):
    class Meta(ValorCatalogo.Meta):
        verbose_name = "criticidad"
        verbose_name_plural = "criticidades"
        constraints = ValorCatalogo.restricciones("catalogo_criticidad")


class TipoServicio(ValorCatalogo):
    class Meta(ValorCatalogo.Meta):
        verbose_name = "tipo de servicio"
        verbose_name_plural = "tipos de servicio"
        constraints = ValorCatalogo.restricciones("catalogo_tiposervicio")


class ServicioNivel1(RegistroCatalogo):
    codigo = models.CharField(
        "código",
        max_length=20,
        unique=True,
        error_messages={"unique": "Ya existe un servicio de nivel 1 con ese código."},
    )
    nombre = models.CharField("nombre", max_length=200)
    # Agregado por diseño: SE.12 tiene conflicto de nombre y debe quedar marcado (D3).
    estado_revision = models.CharField(
        "estado de revisión",
        max_length=20,
        choices=EstadoRevision.choices,
        default=EstadoRevision.SIN_OBSERVACIONES,
    )

    class Meta:
        verbose_name = "servicio de nivel 1"
        verbose_name_plural = "servicios de nivel 1"
        ordering = ["codigo"]
        constraints = [
            _ck_no_vacio("codigo", "catalogo_servicionivel1"),
            _ck_no_vacio("nombre", "catalogo_servicionivel1"),
            _ck_estado_revision("catalogo_servicionivel1"),
        ]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"

    def get_absolute_url(self):
        return reverse("catalogo:servicionivel1_detalle", args=[self.pk])

    def dependientes_activos(self):
        if not self.pk:
            return []
        return list(self.servicios_nivel2.filter(activo=True).order_by("codigo"))


class ServicioNivel2(RegistroCatalogo):
    # Referencias a otras entidades y nombre del campo en los mensajes. Al crear, al cambiarlas o
    # al reactivar el servicio deben estar activas; si no cambian se conservan (como en
    # organización).
    REFERENCIAS = ("nivel1", "clase", "criticidad", "tipo")

    codigo = models.CharField("código", max_length=20)
    # Columna C tal cual; NULL solo en servicios creados en la aplicación. No editable. Clave
    # natural de la importación (modelo-datos.md §6).
    codigo_original = models.CharField(
        "código original", max_length=20, null=True, blank=True, editable=False
    )
    nivel1 = models.ForeignKey(
        ServicioNivel1,
        on_delete=models.PROTECT,
        related_name="servicios_nivel2",
        verbose_name="servicio de nivel 1",
    )
    nombre = models.CharField("nombre", max_length=200)
    # Columna E, texto original (D8). NULL = desconocido; nunca cadena vacía.
    activo_excel = models.TextField("ACTIVO (Excel)", null=True, blank=True)
    clase = models.ForeignKey(
        ClaseServicio,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="servicios",
        verbose_name="clase de servicio",
    )
    criticidad = models.ForeignKey(
        Criticidad,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="servicios",
        verbose_name="criticidad",
    )
    tipo = models.ForeignKey(
        TipoServicio,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="servicios",
        verbose_name="tipo de servicio",
    )
    descripcion = models.TextField("descripción", null=True, blank=True)
    metrica = models.CharField("métrica", max_length=200, null=True, blank=True)
    minimo = models.DecimalField("mínimo", max_digits=14, decimal_places=4, null=True, blank=True)
    maximo = models.DecimalField("máximo", max_digits=14, decimal_places=4, null=True, blank=True)
    estado_revision = models.CharField(
        "estado de revisión",
        max_length=20,
        choices=EstadoRevision.choices,
        default=EstadoRevision.SIN_OBSERVACIONES,
    )
    # Datos nuevos del parcial (no vienen del Excel).
    seccion_responsable = models.ForeignKey(
        "organizacion.Seccion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="servicios_asignados",
        verbose_name="sección responsable",
    )
    usuario_responsable = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="servicios_asignados",
        verbose_name="usuario responsable",
    )

    class Meta:
        verbose_name = "servicio de nivel 2"
        verbose_name_plural = "servicios de nivel 2"
        ordering = ["codigo"]
        indexes = [
            models.Index(fields=["activo"], name="ix_n2_activo"),
            models.Index(fields=["activo_excel"], name="ix_n2_activo_excel"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="uq_n2_codigo",
                violation_error_message="Ya existe un servicio de nivel 2 con ese código.",
            ),
            models.UniqueConstraint(
                fields=["codigo_original"],
                condition=models.Q(codigo_original__isnull=False),
                name="uq_n2_codigo_original",
            ),
            models.CheckConstraint(
                condition=models.Q(minimo__isnull=True)
                | models.Q(maximo__isnull=True)
                | models.Q(minimo__lte=models.F("maximo")),
                name="ck_n2_minimo_le_maximo",
                violation_error_message="El mínimo no puede ser mayor que el máximo.",
            ),
            models.CheckConstraint(
                condition=models.Q(usuario_responsable__isnull=True)
                | models.Q(seccion_responsable__isnull=False),
                name="ck_n2_usuario_requiere_seccion",
                violation_error_message="Un usuario responsable requiere una sección responsable.",
            ),
            models.CheckConstraint(
                condition=models.Q(activo_excel__isnull=True) | ~models.Q(activo_excel=""),
                name="ck_n2_activo_excel_no_vacio",
            ),
            _ck_no_vacio("codigo", "catalogo_servicionivel2"),
            _ck_no_vacio("nombre", "catalogo_servicionivel2"),
            _ck_estado_revision("catalogo_servicionivel2"),
        ]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"

    def get_absolute_url(self):
        return reverse("catalogo:servicionivel2_detalle", args=[self.pk])

    @property
    def activo_excel_reconocido(self):
        return self.activo_excel is None or self.activo_excel in ACTIVO_EXCEL_RECONOCIDOS

    def clean(self):
        super().clean()
        errores = {}
        se_reactiva = self._se_reactiva()
        for campo in self.REFERENCIAS:
            if getattr(self, f"{campo}_id") is None:
                continue
            valor = getattr(self, campo)
            if (self._cambia(f"{campo}_id") or se_reactiva) and not valor.activo:
                nombre = self._meta.get_field(campo).verbose_name
                errores[campo] = f"«{valor}» ({nombre}) está inactivo; elija un valor activo."
        seccion = self.seccion_responsable if self.seccion_responsable_id else None
        usuario = self.usuario_responsable if self.usuario_responsable_id else None
        errores.update(
            validar_responsables(
                seccion,
                usuario,
                verificar_seccion_activa=self._cambia("seccion_responsable_id") or se_reactiva,
                verificar_usuario_activo=self._cambia("usuario_responsable_id") or se_reactiva,
            )
        )
        if self.minimo is not None and self.maximo is not None and self.minimo > self.maximo:
            errores["maximo"] = (
                f"El mínimo ({self.minimo.normalize():f}) no puede ser mayor que el máximo "
                f"({self.maximo.normalize():f})."
            )
        if errores:
            raise ValidationError(errores)
