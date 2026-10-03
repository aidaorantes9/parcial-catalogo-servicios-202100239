"""Estructura organizacional: Empresa → Área → Departamento → Sección → Puesto.

El último nivel, Usuario, está en la app `cuentas`.

Reglas (AGENTS.md §4, modelo-datos.md §3.1):
- Cada registro tiene exactamente un padre (Empresa no tiene padre); la FK es NOT NULL y PROTECT.
- Código único global en Empresa y único dentro del padre en el resto.
- Baja lógica con `activo`; no hay borrado físico desde la aplicación.
- No se crean asociaciones nuevas con padres inactivos ni se reactiva un hijo bajo un padre
  inactivo.
- Desactivar con dependientes activos se rechaza y se listan los dependientes (D1).
"""

from django.core.exceptions import ValidationError
from django.db import models


def _ck_no_vacio(campo, tabla):
    return models.CheckConstraint(
        condition=~models.Q(**{f"{campo}__regex": r"^\s*$"}),
        name=f"ck_{tabla}_{campo}_no_vacio",
    )


class UnidadOrganizacional(models.Model):
    """Campos y validaciones comunes de las cinco entidades de la jerarquía."""

    # Nombre del campo FK al padre; None solo en Empresa.
    campo_padre = None
    # related_name de los hijos activos que impiden desactivar (D1).
    relacion_hijos = None

    codigo = models.CharField("código", max_length=20)
    nombre = models.CharField("nombre", max_length=200)
    activo = models.BooleanField("activo", default=True)
    # Agregado por diseño: identifica la estructura mínima creada por `crear_cuentas_demo`
    # (dato nuevo, no proviene del Excel).
    es_demo = models.BooleanField("dato de demostración", default=False)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        abstract = True
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"

    @classmethod
    def from_db(cls, db, field_names, values):
        instancia = super().from_db(db, field_names, values)
        # Valores leídos de la base, para distinguir altas, cambios de padre y cambios de estado.
        instancia._original = dict(zip(field_names, values, strict=True))
        return instancia

    def _original_de(self, campo):
        return getattr(self, "_original", {}).get(campo)

    @property
    def padre(self):
        return getattr(self, self.campo_padre) if self.campo_padre else None

    @classmethod
    def modelo_padre(cls):
        return cls._meta.get_field(cls.campo_padre).related_model if cls.campo_padre else None

    @classmethod
    def con_jerarquia(cls):
        """Consulta que trae en un solo JOIN todos los niveles superiores hasta la empresa."""
        partes, modelo = [], cls
        while modelo.campo_padre:
            partes.append(modelo.campo_padre)
            modelo = modelo.modelo_padre()
        consulta = cls.objects.all()
        return consulta.select_related("__".join(partes)) if partes else consulta

    def ancestros(self):
        """Niveles superiores, de la empresa al padre directo."""
        cadena, nivel = [], self.padre
        while nivel is not None:
            cadena.insert(0, nivel)
            nivel = nivel.padre
        return cadena

    @property
    def ruta(self):
        """Códigos de los niveles superiores y el registro: «EMP / AR / DP — Nombre»."""
        return " / ".join([n.codigo for n in self.ancestros()] + [str(self)])

    def dependientes_activos(self):
        """Hijos activos que impiden la baja lógica (D1)."""
        if not self.pk or not self.relacion_hijos:
            return []
        return list(getattr(self, self.relacion_hijos).filter(activo=True))

    def clean(self):
        super().clean()
        self._validar_padre_activo()
        self._validar_desactivacion()

    def _validar_padre_activo(self):
        if not self.campo_padre:
            return
        padre_id = getattr(self, f"{self.campo_padre}_id")
        if padre_id is None:
            return  # La validación del campo obligatorio ya informa el error.
        es_alta = self._state.adding
        cambia_padre = not es_alta and padre_id != self._original_de(f"{self.campo_padre}_id")
        se_reactiva = not es_alta and self.activo and self._original_de("activo") is False
        if (es_alta or cambia_padre or se_reactiva) and not self.padre.activo:
            raise ValidationError(
                {
                    self.campo_padre: f"«{self.padre}» está inactivo; no se le pueden asociar "
                    "registros nuevos ni reactivar registros bajo él."
                }
            )

    def _validar_desactivacion(self):
        if self._state.adding or self.activo or self._original_de("activo") is not True:
            return
        dependientes = self.dependientes_activos()
        if dependientes:
            lista = ", ".join(str(d) for d in dependientes)
            raise ValidationError(
                f"No se puede desactivar «{self}»: tiene dependientes activos ({lista}). "
                "Desactívelos o reasígnelos primero."
            )


class Empresa(UnidadOrganizacional):
    relacion_hijos = "areas"

    codigo = models.CharField("código", max_length=20, unique=True)

    class Meta(UnidadOrganizacional.Meta):
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        constraints = [
            _ck_no_vacio("codigo", "organizacion_empresa"),
            _ck_no_vacio("nombre", "organizacion_empresa"),
        ]


class Area(UnidadOrganizacional):
    campo_padre = "empresa"
    relacion_hijos = "departamentos"

    empresa = models.ForeignKey(
        Empresa, on_delete=models.PROTECT, related_name="areas", verbose_name="empresa"
    )

    class Meta(UnidadOrganizacional.Meta):
        verbose_name = "área"
        verbose_name_plural = "áreas"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo"],
                name="uq_organizacion_area_padre_codigo",
                violation_error_message="Ya existe un área con ese código en la empresa.",
            ),
            _ck_no_vacio("codigo", "organizacion_area"),
            _ck_no_vacio("nombre", "organizacion_area"),
        ]


class Departamento(UnidadOrganizacional):
    campo_padre = "area"
    relacion_hijos = "secciones"

    area = models.ForeignKey(
        Area, on_delete=models.PROTECT, related_name="departamentos", verbose_name="área"
    )

    class Meta(UnidadOrganizacional.Meta):
        verbose_name = "departamento"
        verbose_name_plural = "departamentos"
        constraints = [
            models.UniqueConstraint(
                fields=["area", "codigo"],
                name="uq_organizacion_departamento_padre_codigo",
                violation_error_message="Ya existe un departamento con ese código en el área.",
            ),
            _ck_no_vacio("codigo", "organizacion_departamento"),
            _ck_no_vacio("nombre", "organizacion_departamento"),
        ]


class Seccion(UnidadOrganizacional):
    campo_padre = "departamento"
    relacion_hijos = "puestos"

    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name="secciones",
        verbose_name="departamento",
    )

    class Meta(UnidadOrganizacional.Meta):
        verbose_name = "sección"
        verbose_name_plural = "secciones"
        constraints = [
            models.UniqueConstraint(
                fields=["departamento", "codigo"],
                name="uq_organizacion_seccion_padre_codigo",
                violation_error_message="Ya existe una sección con ese código en el departamento.",
            ),
            _ck_no_vacio("codigo", "organizacion_seccion"),
            _ck_no_vacio("nombre", "organizacion_seccion"),
        ]

    def dependientes_activos(self):
        # D1 extendido: además de los puestos activos, los servicios activos de los que es
        # sección responsable.
        if not self.pk:
            return []
        servicios = self.servicios_asignados.filter(activo=True).order_by("codigo")
        return super().dependientes_activos() + list(servicios)


class Puesto(UnidadOrganizacional):
    campo_padre = "seccion"

    seccion = models.ForeignKey(
        Seccion, on_delete=models.PROTECT, related_name="puestos", verbose_name="sección"
    )

    class Meta(UnidadOrganizacional.Meta):
        verbose_name = "puesto"
        verbose_name_plural = "puestos"
        constraints = [
            models.UniqueConstraint(
                fields=["seccion", "codigo"],
                name="uq_organizacion_puesto_padre_codigo",
                violation_error_message="Ya existe un puesto con ese código en la sección.",
            ),
            _ck_no_vacio("codigo", "organizacion_puesto"),
            _ck_no_vacio("nombre", "organizacion_puesto"),
        ]

    def dependientes_activos(self):
        # Los dependientes de un puesto son sus usuarios (campo is_active por exigencia de Django).
        if not self.pk:
            return []
        return list(self.usuarios.filter(is_active=True))

    def clean(self):
        super().clean()
        self._validar_cambio_de_seccion()

    def _validar_cambio_de_seccion(self):
        """D9: mover el puesto a otra sección cambiaría la sección de sus usuarios; se rechaza si
        alguno es usuario responsable de servicios (de cualquier estado)."""
        original = self._original_de("seccion_id")
        if self._state.adding or self.seccion_id is None or self.seccion_id == original:
            return
        responsables = [u for u in self.usuarios.all() if u.servicios_asignados.exists()]
        if responsables:
            lista = ", ".join(u.username for u in responsables)
            raise ValidationError(
                {
                    "seccion": f"No se puede mover el puesto a otra sección: sus usuarios {lista} "
                    "son responsables de servicios de la sección actual. Cambie primero el "
                    "usuario responsable de esos servicios."
                }
            )
