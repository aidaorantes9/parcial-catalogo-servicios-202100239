"""Trazabilidad de la importación del Excel (modelo-datos.md §3.2 y §3.4).

Estos modelos solo los escribe el importador (fase siguiente); la aplicación los muestra en las
fichas de servicio. El mapeo de correcciones se carga con una migración de datos versionada.
"""

from django.contrib.postgres.fields import ArrayField
from django.db import models


class AmbitoCorreccion(models.TextChoices):
    ETIQUETA_CLASE = "ETIQUETA_CLASE", "Etiqueta de clase"
    ETIQUETA_CRITICIDAD = "ETIQUETA_CRITICIDAD", "Etiqueta de criticidad"
    ETIQUETA_TIPO = "ETIQUETA_TIPO", "Etiqueta de tipo"
    NOMBRE_N1 = "NOMBRE_N1", "Nombre de nivel 1"
    NOMBRE_N2 = "NOMBRE_N2", "Nombre de nivel 2"
    CODIGO_N2 = "CODIGO_N2", "Código de nivel 2"


class MapeoCorreccion(models.Model):
    """Regla de corrección de un texto del Excel; el importador la consulta por
    `(ambito, valor_original)`. Sin FK: es una tabla de reglas."""

    ambito = models.CharField("ámbito", max_length=30, choices=AmbitoCorreccion.choices)
    valor_original = models.TextField("valor original")
    valor_corregido = models.TextField("valor corregido")
    celda_origen = models.CharField("celda de origen", max_length=20, null=True, blank=True)
    motivo = models.TextField("motivo")
    activo = models.BooleanField("activo", default=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "mapeo de corrección"
        verbose_name_plural = "mapeos de corrección"
        constraints = [
            models.UniqueConstraint(
                fields=["ambito", "valor_original"], name="uq_mapeocorreccion_ambito_valor"
            ),
            models.CheckConstraint(
                condition=models.Q(ambito__in=AmbitoCorreccion.values),
                name="ck_mapeocorreccion_ambito",
            ),
            models.CheckConstraint(
                condition=~models.Q(valor_corregido=models.F("valor_original")),
                name="ck_mapeocorreccion_cambia_valor",
            ),
        ]

    def __str__(self):
        return f"{self.ambito}: {self.valor_original!r} → {self.valor_corregido!r}"


class EstadoEjecucion(models.TextChoices):
    EN_CURSO = "EN_CURSO", "En curso"
    EXITOSA = "EXITOSA", "Exitosa"
    FALLIDA = "FALLIDA", "Fallida"


class Ejecucion(models.Model):
    """Una fila por cada ejecución del importador, también las repetidas (P07)."""

    iniciada_en = models.DateTimeField("iniciada en", auto_now_add=True)
    finalizada_en = models.DateTimeField("finalizada en", null=True, blank=True)
    archivo_nombre = models.CharField("archivo", max_length=255)
    archivo_sha256 = models.CharField("SHA-256 del archivo", max_length=64)
    hoja = models.CharField("hoja", max_length=100, default="Servicios Externos")
    estado = models.CharField(
        "estado", max_length=10, choices=EstadoEjecucion.choices, default=EstadoEjecucion.EN_CURSO
    )
    creados = models.PositiveIntegerField("creados", default=0)
    actualizados = models.PositiveIntegerField("actualizados", default=0)
    # Agregado por diseño: en una repetición todo cae aquí y el resumen cuadra.
    sin_cambios = models.PositiveIntegerField("sin cambios", default=0)
    omitidos = models.PositiveIntegerField("omitidos", default=0)
    observados = models.PositiveIntegerField("observados", default=0)
    total_n1 = models.PositiveIntegerField("códigos de nivel 1", null=True, blank=True)
    total_n2 = models.PositiveIntegerField("códigos de nivel 2", null=True, blank=True)
    detalle_conteos = models.JSONField("detalle de conteos", default=dict, blank=True)
    ejecutada_por = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="importaciones",
        verbose_name="ejecutada por",
    )
    mensaje_error = models.TextField("mensaje de error", null=True, blank=True)

    class Meta:
        verbose_name = "ejecución de importación"
        verbose_name_plural = "ejecuciones de importación"
        ordering = ["-iniciada_en", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(finalizada_en__isnull=True)
                | models.Q(finalizada_en__gte=models.F("iniciada_en")),
                name="ck_ejecucion_finalizada_tras_inicio",
            ),
            models.CheckConstraint(
                condition=models.Q(archivo_sha256__regex=r"^[0-9a-f]{64}$"),
                name="ck_ejecucion_sha256",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoEjecucion.values), name="ck_ejecucion_estado"
            ),
        ]

    def __str__(self):
        return f"Importación #{self.pk} ({self.get_estado_display()})"


class AccionOrigen(models.TextChoices):
    CREADO = "CREADO", "Creado"
    ACTUALIZADO = "ACTUALIZADO", "Actualizado"
    SIN_CAMBIOS = "SIN_CAMBIOS", "Sin cambios"


class OrigenServicio(models.Model):
    """Origen vigente de un servicio importado (nivel 1 o nivel 2, uno por servicio)."""

    servicio_nivel1 = models.OneToOneField(
        "catalogo.ServicioNivel1",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="origen",
    )
    servicio_nivel2 = models.OneToOneField(
        "catalogo.ServicioNivel2",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="origen",
    )
    hoja = models.CharField("hoja", max_length=100)
    filas = ArrayField(models.IntegerField(), verbose_name="filas")
    rangos_combinados = ArrayField(
        models.CharField(max_length=20), default=list, blank=True, verbose_name="rangos combinados"
    )
    # {"C": {"celda": "C5", "valor": "SE.01.01"}, ...}
    valores_originales = models.JSONField("valores originales")
    # [{"campo": "minimo", "regla": "vacio_a_null"}, ...]
    transformaciones = models.JSONField("transformaciones", default=list, blank=True)
    primera_ejecucion = models.ForeignKey(
        Ejecucion, on_delete=models.PROTECT, related_name="origenes_creados"
    )
    ultima_ejecucion = models.ForeignKey(
        Ejecucion, on_delete=models.PROTECT, related_name="origenes_actualizados"
    )
    ultima_accion = models.CharField("última acción", max_length=12, choices=AccionOrigen.choices)

    class Meta:
        verbose_name = "origen de servicio"
        verbose_name_plural = "orígenes de servicio"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(servicio_nivel1__isnull=False, servicio_nivel2__isnull=True)
                | models.Q(servicio_nivel1__isnull=True, servicio_nivel2__isnull=False),
                name="ck_origen_un_servicio",
            ),
            models.CheckConstraint(condition=models.Q(filas__len__gte=1), name="ck_origen_filas"),
            models.CheckConstraint(
                condition=models.Q(ultima_accion__in=AccionOrigen.values),
                name="ck_origen_ultima_accion",
            ),
        ]

    def __str__(self):
        return f"{self.hoja}, filas {self.filas}"


class TipoObservacion(models.TextChoices):
    CONFLICTO_NOMBRE_N1 = "CONFLICTO_NOMBRE_N1", "Conflicto de nombre de nivel 1"
    FILA_SIN_CODIGO = "FILA_SIN_CODIGO", "Fila sin código"
    PADRE_POR_PREFIJO = "PADRE_POR_PREFIJO", "Nivel 1 asignado por prefijo"
    ATRIBUTOS_AUSENTES = "ATRIBUTOS_AUSENTES", "Atributos ausentes"
    CODIGO_FORMATO_NO_ESTANDAR = "CODIGO_FORMATO_NO_ESTANDAR", "Código con formato no estándar"
    CORRECCION_APLICADA = "CORRECCION_APLICADA", "Corrección aplicada"
    POSIBLE_ERROR_ESCRITURA = "POSIBLE_ERROR_ESCRITURA", "Posible error de escritura"
    VALOR_NO_RECONOCIDO = "VALOR_NO_RECONOCIDO", "Valor no reconocido"
    TEXTO_CON_FORMA_DE_INSTRUCCION = (
        "TEXTO_CON_FORMA_DE_INSTRUCCION",
        "Texto con forma de instrucción",
    )
    ESPACIOS_EN_TEXTO = "ESPACIOS_EN_TEXTO", "Espacios en el texto"
    AUSENCIA_EN_CONTINUACION = "AUSENCIA_EN_CONTINUACION", "Ausencia en filas de continuación"
    CONTROL_CONTEO = "CONTROL_CONTEO", "Control de conteo"


class Severidad(models.TextChoices):
    INFO = "INFO", "Información"
    ADVERTENCIA = "ADVERTENCIA", "Advertencia"
    ERROR = "ERROR", "Error"


class Observacion(models.Model):
    ejecucion = models.ForeignKey(Ejecucion, on_delete=models.PROTECT, related_name="observaciones")
    tipo = models.CharField("tipo", max_length=40, choices=TipoObservacion.choices)
    severidad = models.CharField(
        "severidad", max_length=12, choices=Severidad.choices, default=Severidad.ADVERTENCIA
    )
    # Código tal como en el Excel; NULL en filas sin código (42, 67).
    codigo_afectado = models.CharField("código afectado", max_length=20, null=True, blank=True)
    servicio_nivel1 = models.ForeignKey(
        "catalogo.ServicioNivel1",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="observaciones",
    )
    servicio_nivel2 = models.ForeignKey(
        "catalogo.ServicioNivel2",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="observaciones",
    )
    filas = ArrayField(models.IntegerField(), verbose_name="filas")
    celdas = ArrayField(
        models.CharField(max_length=20), default=list, blank=True, verbose_name="celdas"
    )
    detalle = models.TextField("detalle")
    valores_conflicto = models.JSONField("valores en conflicto", null=True, blank=True)
    regla_aplicada = models.TextField("regla aplicada", null=True, blank=True)

    class Meta:
        verbose_name = "observación de importación"
        verbose_name_plural = "observaciones de importación"
        ordering = ["pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tipo__in=TipoObservacion.values), name="ck_observacion_tipo"
            ),
            models.CheckConstraint(
                condition=models.Q(severidad__in=Severidad.values),
                name="ck_observacion_severidad",
            ),
            models.CheckConstraint(
                condition=models.Q(filas__len__gte=1), name="ck_observacion_filas"
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} ({self.codigo_afectado or 'sin código'})"
