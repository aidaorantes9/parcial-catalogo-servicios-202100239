"""Importador idempotente y trazable del catálogo (enunciado §3.4, modelo-datos.md §3.4 y §6).

Reglas aplicadas (AGENTS.md §5, decisiones D2–D8):
- Archivo original (ruta por defecto): el SHA-256 debe coincidir con la suma esperada o se aborta, y
  los controles 12/46 son obligatorios. Otro archivo (`--archivo`): se registra su SHA-256 sin
  compararlo (salvo que se indique una suma con `--sha256`) y los controles solo se informan, salvo
  `exigir_controles`.
- Una referencia a un nivel 1 o a un valor de catálogo dado de baja no aborta la importación: el
  servicio existente conserva sus valores (acción OBSERVADO) y se emite REFERENCIA_INACTIVA; un
  servicio nuevo cuyo nivel 1 está inactivo no se crea (fila omitida).
- Upsert por clave natural: N1 por `codigo`, N2 por `codigo_original`, valores de catálogo por
  `etiqueta_original`. Repetir la importación no duplica registros ni observaciones.
- Solo se sobrescriben campos que vienen del Excel (S7): nunca responsables, baja lógica (`activo`),
  `codigo` de un N2 existente, `orden` de un valor existente ni un `estado_revision = REVISADO`.
- Todo en una transacción: si un control falla (12 N1 / 46 N2) o un registro no valida, no queda
  nada a medias y se registra una ejecución FALLIDA aparte. `dry_run` hace todo y revierte.
- Un dato ausente es NULL, nunca 0 ni cadena vacía (D6). Los textos no se recortan (S11).
"""

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from catalogo.models import (
    ACTIVO_EXCEL_RECONOCIDOS,
    ClaseServicio,
    Criticidad,
    EstadoRevision,
    ServicioNivel1,
    ServicioNivel2,
    TipoServicio,
)
from catalogo.servicios import guardar_servicio_nivel2
from importacion import lector
from importacion.models import (
    AccionOrigen,
    AmbitoCorreccion,
    Ejecucion,
    EstadoEjecucion,
    MapeoCorreccion,
    Observacion,
    OrigenServicio,
    Severidad,
    TipoObservacion,
)

ARCHIVO_POR_DEFECTO = "data/CatalogoServicios.xlsx"
SHA256_POR_DEFECTO = "data/CatalogoServicios.xlsx.sha256"
ESPERADO_N1 = 12
ESPERADO_N2 = 46

# Catálogo de cada lista: (modelo, columna de los servicios, ámbito del mapeo de correcciones).
CATALOGOS = {
    "clase": (ClaseServicio, "F", AmbitoCorreccion.ETIQUETA_CLASE),
    "criticidad": (Criticidad, "G", AmbitoCorreccion.ETIQUETA_CRITICIDAD),
    "tipo": (TipoServicio, "H", AmbitoCorreccion.ETIQUETA_TIPO),
}
# Columnas cuya ausencia deja al servicio sin un atributo esperado (D6). I, K y L son opcionales:
# están vacías en casi todo el Excel, así que su vacío solo se registra como transformación.
COLUMNAS_ESPERADAS = {"E": "ACTIVO", "F": "clase", "G": "criticidad", "H": "tipo", "J": "métrica"}

# Posibles errores de escritura en nombres que se observan pero NO se corrigen (D7, ajuste). Lista
# cerrada tomada del análisis del Excel; no es un corrector automático.
POSIBLES_ERRORES_ESCRITURA = {"Análsis": "Análisis"}

# Patrones de texto con forma de instrucción (mismos que scripts/analizar_excel.py). Coincidir no
# ejecuta nada: solo se registra la observación (AGENTS.md §9).
PATRONES_INSTRUCCION = [
    r"\bignor",
    r"\binstrucci",
    r"\bprompt\b",
    r"\bsystem\b",
    r"\bsistema:",
    r"\bejecut",
    r"\bborr",
    r"\belimin",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\brm\s+-",
    r"\bcurl\b",
    r"\bwget\b",
    r"\bpassword\b",
    r"\bcontrase",
    r"\bsecret",
    r"\btoken\b",
    r"\bapi[_ ]?key",
    r"\brevel",
    r"\bmuestr",
    r"\benv[ií]a",
    r"\bolvid",
    r"\bact[uú]a como\b",
    r"\bassistant\b",
    r"\basistente\b",
    r"\bIA\b",
    r"\bAI\b",
    r"https?://",
    r"\bcommit\b",
    r"\bpush\b",
]

# Severidad por tipo. ADVERTENCIA o ERROR dejan el registro en PENDIENTE_REVISION.
SEVERIDAD = {
    TipoObservacion.CONFLICTO_NOMBRE_N1: Severidad.ADVERTENCIA,
    TipoObservacion.FILA_SIN_CODIGO: Severidad.ADVERTENCIA,
    TipoObservacion.PADRE_POR_PREFIJO: Severidad.ADVERTENCIA,
    TipoObservacion.ATRIBUTOS_AUSENTES: Severidad.ADVERTENCIA,
    TipoObservacion.CODIGO_FORMATO_NO_ESTANDAR: Severidad.INFO,
    TipoObservacion.CORRECCION_APLICADA: Severidad.INFO,
    TipoObservacion.POSIBLE_ERROR_ESCRITURA: Severidad.ADVERTENCIA,
    TipoObservacion.VALOR_NO_RECONOCIDO: Severidad.ADVERTENCIA,
    TipoObservacion.TEXTO_CON_FORMA_DE_INSTRUCCION: Severidad.ADVERTENCIA,
    TipoObservacion.ESPACIOS_EN_TEXTO: Severidad.INFO,
    TipoObservacion.AUSENCIA_EN_CONTINUACION: Severidad.INFO,
    TipoObservacion.CONFLICTO_ATRIBUTOS: Severidad.ADVERTENCIA,
    TipoObservacion.REFERENCIA_INACTIVA: Severidad.ADVERTENCIA,
}
REQUIEREN_REVISION = (Severidad.ADVERTENCIA, Severidad.ERROR)

CAMPOS_N1 = ("nombre",)
CAMPOS_N2 = (
    "nivel1_id",
    "nombre",
    "activo_excel",
    "clase_id",
    "criticidad_id",
    "tipo_id",
    "descripcion",
    "metrica",
    "minimo",
    "maximo",
)
ENTIDADES = ("clase", "criticidad", "tipo", "nivel1", "nivel2")
CLAVE_CONTEO = {
    AccionOrigen.CREADO: "creados",
    AccionOrigen.ACTUALIZADO: "actualizados",
    AccionOrigen.SIN_CAMBIOS: "sin_cambios",
    AccionOrigen.OBSERVADO: "observados",
}
ACCIONES_CONTEO = tuple(CLAVE_CONTEO.values())
# Columna del Excel de cada referencia del servicio de nivel 2 (para REFERENCIA_INACTIVA).
COLUMNA_REFERENCIA = {"nivel1": "A", **{n: c for n, (_, c, _) in CATALOGOS.items()}}


class ErrorImportacion(Exception):
    """La importación no se completó. `resultado` trae lo calculado hasta el fallo, si existe."""

    def __init__(self, mensaje, resultado=None):
        super().__init__(mensaje)
        self.resultado = resultado


class _Revertir(Exception):
    """Revierte la transacción de un dry-run conservando el resultado."""

    def __init__(self, resultado):
        super().__init__("dry-run")
        self.resultado = resultado


@dataclass
class Resultado:
    archivo: str
    sha256: str
    dry_run: bool
    es_original: bool = True
    controles_exigidos: bool = True
    conteos: dict = field(
        default_factory=lambda: {e: dict.fromkeys(ACCIONES_CONTEO, 0) for e in ENTIDADES}
    )
    # Códigos distintos encontrados en el archivo (los controles cuentan registros en la base).
    codigos_archivo: dict = field(default_factory=dict)
    filas: dict = field(default_factory=dict)
    # Observaciones emitidas en esta ejecución: dicts con «nueva» = no existía antes.
    observaciones: list = field(default_factory=list)
    total_n1: int | None = None
    total_n2: int | None = None
    ejecucion_id: int | None = None
    estado: str = EstadoEjecucion.EN_CURSO
    mensaje_error: str | None = None

    def total(self, accion):
        return sum(c[accion] for c in self.conteos.values())

    @property
    def omitidos(self):
        return sum(len(f) for motivo, f in self.filas.items() if motivo != "servicio")

    @property
    def controles_pasan(self):
        return self.control_n1 and self.control_n2

    @property
    def control_n1(self):
        return self.total_n1 == ESPERADO_N1

    @property
    def control_n2(self):
        return self.total_n2 == ESPERADO_N2

    def por_tipo(self):
        conteo = {}
        for o in self.observaciones:
            conteo[o["tipo"]] = conteo.get(o["tipo"], 0) + 1
        return dict(sorted(conteo.items()))

    def detalle_conteos(self):
        return {
            **self.conteos,
            "archivo_original": self.es_original,
            "controles_exigidos": self.controles_exigidos,
            "codigos_en_archivo": self.codigos_archivo,
            "filas": {motivo: len(f) for motivo, f in self.filas.items()},
            "observaciones": {
                "emitidas": len(self.observaciones),
                "nuevas": sum(1 for o in self.observaciones if o["nueva"]),
                "por_tipo": self.por_tipo(),
            },
            "controles": {
                "nivel1": {"esperado": ESPERADO_N1, "obtenido": self.total_n1},
                "nivel2": {"esperado": ESPERADO_N2, "obtenido": self.total_n2},
            },
        }


def sha256_de(contenido):
    return hashlib.sha256(contenido).hexdigest()


def leer_sha256_esperado(ruta):
    """Primer campo de un archivo con formato `sha256sum` («<hash>  <archivo>»)."""
    try:
        texto = Path(ruta).read_text(encoding="utf-8").split()
    except OSError as error:
        raise ErrorImportacion(f"No se pudo leer la suma esperada {ruta}: {error}") from error
    if not texto or not re.fullmatch(r"[0-9a-f]{64}", texto[0].lower()):
        raise ErrorImportacion(f"{ruta} no contiene un SHA-256 válido.")
    return texto[0].lower()


def es_archivo_original(archivo):
    return Path(archivo).resolve() == Path(ARCHIVO_POR_DEFECTO).resolve()


def importar(
    archivo=ARCHIVO_POR_DEFECTO,
    sha256=None,
    *,
    dry_run=False,
    usuario=None,
    exigir_controles=False,
):
    """Importa el libro y devuelve el `Resultado`. Lanza `ErrorImportacion` si aborta.

    `sha256`: archivo de suma esperada. Con el archivo original, por defecto
    `SHA256_POR_DEFECTO`; con otro archivo solo se verifica si se indica.
    """
    try:
        contenido = Path(archivo).read_bytes()
    except OSError as error:
        raise ErrorImportacion(f"No se pudo leer el archivo {archivo}: {error}") from error
    es_original = es_archivo_original(archivo)
    resultado = Resultado(
        archivo=str(archivo),
        sha256=sha256_de(contenido),
        dry_run=dry_run,
        es_original=es_original,
        controles_exigidos=es_original or exigir_controles,
    )
    if es_original and sha256 is None:
        sha256 = SHA256_POR_DEFECTO
    try:
        if sha256 is not None:
            esperado = leer_sha256_esperado(sha256)
            if resultado.sha256 != esperado:
                raise ErrorImportacion(
                    f"El SHA-256 de {archivo} ({resultado.sha256}) no coincide con el esperado "
                    f"en {sha256} ({esperado}). El archivo no es el original: no se importa nada.",
                    resultado,
                )
        with transaction.atomic():
            # Evita dos importaciones simultáneas (el bloqueo se libera al terminar la transacción).
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(hashtext('importar_catalogo'))")
            _Importacion(contenido, resultado, usuario).ejecutar()
            if resultado.controles_exigidos and not resultado.controles_pasan:
                raise ErrorImportacion(
                    f"Controles no superados: nivel 1 = {resultado.total_n1} (esperado "
                    f"{ESPERADO_N1}), nivel 2 = {resultado.total_n2} (esperado {ESPERADO_N2}). "
                    "Se revierte la importación.",
                    resultado,
                )
            if dry_run:
                raise _Revertir(resultado)
    except _Revertir:
        resultado.estado = EstadoEjecucion.EXITOSA
        resultado.ejecucion_id = None
        return resultado
    except ErrorImportacion as error:
        _registrar_fallida(resultado, str(error), usuario)
        error.resultado = resultado
        raise
    except (lector.ErrorLectura, ValidationError, DatabaseError) as error:
        mensaje = _mensaje(error)
        _registrar_fallida(resultado, mensaje, usuario)
        raise ErrorImportacion(mensaje, resultado) from error
    return resultado


def _mensaje(error):
    if isinstance(error, ValidationError):
        return "Registro no válido: " + " ".join(error.messages)
    return str(error)


def _registrar_fallida(resultado, mensaje, usuario):
    """Deja constancia de la ejecución abortada (fuera de la transacción revertida)."""
    resultado.estado = EstadoEjecucion.FALLIDA
    resultado.mensaje_error = mensaje
    resultado.ejecucion_id = None
    if resultado.dry_run:
        return
    ejecucion = Ejecucion.objects.create(
        archivo_nombre=resultado.archivo,
        archivo_sha256=resultado.sha256,
        hoja=lector.HOJA,
        estado=EstadoEjecucion.FALLIDA,
        total_n1=resultado.total_n1,
        total_n2=resultado.total_n2,
        ejecutada_por=usuario,
        mensaje_error=mensaje,
    )
    ejecucion.finalizada_en = timezone.now()
    ejecucion.save(update_fields=["finalizada_en"])
    resultado.ejecucion_id = ejecucion.pk


def _a_json(valor):
    """Valor de celda apto para JSONField: str, número, booleano o None; el resto, como texto."""
    if isinstance(valor, dict):
        return {str(k): _a_json(v) for k, v in valor.items()}
    if isinstance(valor, list | tuple):
        return [_a_json(v) for v in valor]
    if valor is None or isinstance(valor, str | int | float | bool):
        return valor
    return str(valor)


def _hay_cambios(registro, campos, nuevos):
    return any(getattr(registro, campo) != nuevos[campo] for campo in campos)


def _codigo_catalogo(etiqueta):
    """Identificador estable de un valor de catálogo: «Very Low» → «VERY_LOW»."""
    sin_tildes = unicodedata.normalize("NFKD", str(etiqueta)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "_", sin_tildes.upper()).strip("_") or "VALOR"


def _texto_opcional(valor):
    """Descripción y métrica: vacía o de solo espacios → NULL; con texto, tal cual (S11)."""
    if valor is None or (isinstance(valor, str) and valor.strip() == ""):
        return None
    return valor if isinstance(valor, str) else str(valor)


def _decimal(valor):
    """K/L: número → Decimal exacto de su texto; cualquier otra cosa no es reconocible."""
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        return None
    return Decimal(str(valor))


class _Importacion:
    def __init__(self, contenido, resultado, usuario):
        self.contenido = contenido
        self.resultado = resultado
        self.usuario = usuario
        self.observaciones = []  # dicts pendientes de guardar

    def ejecutar(self):
        r = self.resultado
        self.ejecucion = Ejecucion.objects.create(
            archivo_nombre=r.archivo,
            archivo_sha256=r.sha256,
            hoja=lector.HOJA,
            ejecutada_por=self.usuario,
        )
        libro = lector.leer_libro(self.contenido)
        r.codigos_archivo = {"nivel1": len(libro.nivel1), "nivel2": len(libro.nivel2)}
        r.filas = {"servicio": [s.fila for s in libro.nivel2]}
        for motivo in ("continuacion", "sin_codigo", "vacia"):
            r.filas[motivo] = [f.fila for f in libro.omitidas if f.motivo == motivo]
        r.filas["referencia_inactiva"] = []

        self.catalogos = {nombre: self._catalogo(nombre, libro) for nombre in CATALOGOS}
        self.nivel1 = {n1.codigo: self._nivel1(n1) for n1 in libro.nivel1}
        for servicio in libro.nivel2:
            self._nivel2(servicio)
        for omitida in libro.omitidas:
            if omitida.motivo == "sin_codigo":
                self._fila_sin_codigo(omitida)
        # Controles: registros que existen en la base para los códigos del archivo, también los
        # dados de baja (un servicio nuevo no creado por nivel 1 inactivo no cuenta).
        r.total_n1 = ServicioNivel1.objects.filter(
            codigo__in=[n1.codigo for n1 in libro.nivel1]
        ).count()
        r.total_n2 = ServicioNivel2.objects.filter(
            codigo_original__in=[s.codigo for s in libro.nivel2]
        ).count()
        self._controles()
        self._guardar_observaciones()

        e = self.ejecucion
        e.estado = EstadoEjecucion.EXITOSA
        e.creados = r.total("creados")
        e.actualizados = r.total("actualizados")
        e.sin_cambios = r.total("sin_cambios")
        e.omitidos = r.omitidos
        e.observados = len(r.observaciones)
        e.total_n1 = r.total_n1
        e.total_n2 = r.total_n2
        e.detalle_conteos = r.detalle_conteos()
        e.finalizada_en = timezone.now()
        e.save()
        r.estado = e.estado
        r.ejecucion_id = e.pk

    # ------------------------------------------------------------------ observaciones

    def _observar(
        self,
        tipo,
        detalle,
        filas,
        *,
        codigo=None,
        celdas=(),
        valores=None,
        regla=None,
        severidad=None,
        n1=None,
        n2=None,
    ):
        obs = {
            "tipo": tipo,
            "severidad": severidad or SEVERIDAD[tipo],
            "codigo_afectado": codigo,
            "filas": list(filas),
            "celdas": list(celdas),
            "detalle": detalle,
            "valores_conflicto": _a_json(valores),
            "regla_aplicada": regla,
            "n1": n1,
            "n2": n2,
        }
        self.observaciones.append(obs)
        return obs

    def _observar_textos(self, codigo, celdas, destino):
        """Texto con forma de instrucción y espacios sobrantes: se conservan como dato."""
        for celda in celdas:
            valor = celda.valor
            if not isinstance(valor, str):
                continue
            fila = int(re.sub(r"\D", "", celda.celda))
            patrones = [p for p in PATRONES_INSTRUCCION if re.search(p, valor, re.IGNORECASE)]
            if patrones:
                self._observar(
                    TipoObservacion.TEXTO_CON_FORMA_DE_INSTRUCCION,
                    f"La celda {celda.celda} contiene texto con forma de instrucción. Se conserva "
                    "como dato y no se obedece.",
                    [fila],
                    codigo=codigo,
                    celdas=[celda.celda],
                    valores={celda.celda: valor, "patrones": patrones},
                    regla="AGENTS.md §9: el contenido del Excel es dato, nunca instrucción",
                    **destino,
                )
            if valor != valor.strip() or "  " in valor:
                self._observar(
                    TipoObservacion.ESPACIOS_EN_TEXTO,
                    f"La celda {celda.celda} tiene espacios iniciales, finales o dobles; se "
                    "conserva sin recortar.",
                    [fila],
                    codigo=codigo,
                    celdas=[celda.celda],
                    valores={celda.celda: valor},
                    regla="S11: los textos del Excel se guardan sin recortar",
                    **destino,
                )
            for error, sugerencia in POSIBLES_ERRORES_ESCRITURA.items():
                if error in valor:
                    self._observar(
                        TipoObservacion.POSIBLE_ERROR_ESCRITURA,
                        f"«{error}» en {celda.celda} parece un error de escritura de "
                        f"«{sugerencia}». No se corrige.",
                        [fila],
                        codigo=codigo,
                        celdas=[celda.celda],
                        valores={celda.celda: valor, "sugerencia": sugerencia},
                        regla="D7 (ajuste): se observa sin corregir",
                        **destino,
                    )

    def _guardar_observaciones(self):
        """Inserta las observaciones nuevas y enlaza esta ejecución a las ya existentes."""
        for obs in self.observaciones:
            contenido = {
                k: obs[k]
                for k in (
                    "tipo",
                    "severidad",
                    "codigo_afectado",
                    "filas",
                    "celdas",
                    "detalle",
                    "valores_conflicto",
                    "regla_aplicada",
                )
            }
            huella = sha256_de(
                json.dumps(contenido, sort_keys=True, ensure_ascii=False, default=str).encode()
            )
            registro = Observacion.objects.filter(huella=huella).first()
            nueva = registro is None
            if nueva:
                registro = Observacion.objects.create(
                    ejecucion=self.ejecucion,
                    huella=huella,
                    servicio_nivel1=obs["n1"],
                    servicio_nivel2=obs["n2"],
                    **contenido,
                )
            elif (registro.servicio_nivel1, registro.servicio_nivel2) != (obs["n1"], obs["n2"]):
                registro.servicio_nivel1, registro.servicio_nivel2 = obs["n1"], obs["n2"]
                registro.save(update_fields=["servicio_nivel1", "servicio_nivel2"])
            registro.ejecuciones.add(self.ejecucion)
            self.resultado.observaciones.append({**contenido, "nueva": nueva, "id": registro.pk})

    # ------------------------------------------------------------------ catálogos

    def _catalogo(self, nombre, libro):
        """Las listas E112:H122 solo alimentan catálogos; nunca crean servicios."""
        modelo, _, ambito = CATALOGOS[nombre]
        correcciones = dict(
            MapeoCorreccion.objects.filter(ambito=ambito, activo=True).values_list(
                "valor_original", "valor_corregido"
            )
        )
        conteo = self.resultado.conteos[nombre]
        for orden, item in enumerate(libro.listas[nombre], start=1):
            etiqueta = item.etiqueta if isinstance(item.etiqueta, str) else str(item.etiqueta)
            mostrada = correcciones.get(etiqueta, etiqueta)
            celda = f"{item.columna}{item.fila}"
            if mostrada != etiqueta:
                self._observar(
                    TipoObservacion.CORRECCION_APLICADA,
                    f"Etiqueta «{etiqueta}» ({celda}) se muestra como «{mostrada}»; la original "
                    "se conserva en etiqueta_original.",
                    [item.fila],
                    celdas=[celda],
                    valores={"original": etiqueta, "corregido": mostrada},
                    regla=f"Mapeo de corrección {ambito} (D7)",
                )
            valor = modelo.objects.filter(etiqueta_original=etiqueta).first()
            if valor is None:
                valor = modelo(
                    codigo=_codigo_catalogo(etiqueta),
                    etiqueta_original=etiqueta,
                    etiqueta_mostrada=mostrada,
                    orden=orden,
                    fila_origen=item.fila,
                )
                valor.full_clean()
                valor.save()
                conteo["creados"] += 1
                continue
            # `orden` y `activo` pueden editarse en la aplicación: no se sobrescriben (S7, S8).
            nuevos = {"etiqueta_mostrada": mostrada, "fila_origen": item.fila}
            if _hay_cambios(valor, nuevos, nuevos):
                for campo, dato in nuevos.items():
                    setattr(valor, campo, dato)
                valor.full_clean()
                valor.save()
                conteo["actualizados"] += 1
            else:
                conteo["sin_cambios"] += 1
        return {v.etiqueta_original: v for v in modelo.objects.all()}

    # ------------------------------------------------------------------ nivel 1

    def _nivel1(self, leido):
        codigo = leido.codigo
        destino_obs = []
        if not leido.nombres:
            raise ErrorImportacion(
                f"El nivel 1 «{codigo}» (filas {leido.filas}) no tiene nombre en la columna B."
            )
        canonico = leido.nombres[0]
        valores = {"A": leido.celda_codigo.como_dict(), "B": canonico.como_dict()}
        distintos = []
        for celda in leido.nombres[1:]:
            valores[f"B ({celda.celda})"] = celda.como_dict()
            if celda.valor != canonico.valor and celda.valor not in distintos:
                distintos.append(celda.valor)
        transformaciones = []
        if distintos:
            transformaciones.append(
                {"campo": "nombre", "regla": f"nombre_canonico_primera_fila ({canonico.celda})"}
            )
            destino_obs.append(
                self._observar(
                    TipoObservacion.CONFLICTO_NOMBRE_N1,
                    f"El código {codigo} tiene nombres distintos en la columna B. Se usa "
                    f"«{canonico.valor}» ({canonico.celda}) y se conservan todos como evidencia.",
                    leido.filas,
                    codigo=codigo,
                    celdas=[c.celda for c in leido.nombres],
                    valores={c.celda: c.valor for c in leido.nombres},
                    regla="D3: nombre canónico = primera fila del grupo (B99)",
                )
            )
        if not lector.RE_COD_N1.match(codigo):
            destino_obs.append(
                self._observar(
                    TipoObservacion.CODIGO_FORMATO_NO_ESTANDAR,
                    f"El código de nivel 1 «{codigo}» no sigue el formato SE.NN; se conserva tal "
                    "cual.",
                    leido.filas[:1],
                    codigo=codigo,
                    celdas=[leido.celda_codigo.celda],
                    valores={leido.celda_codigo.celda: codigo},
                    regla="D5: códigos sin normalizar",
                )
            )
        antes = len(self.observaciones)
        self._observar_textos(codigo, leido.nombres, {})
        destino_obs += self.observaciones[antes:]

        nuevos = {"nombre": canonico.valor}
        registro, accion = self._upsert(
            "nivel1",
            ServicioNivel1.objects.filter(codigo=codigo).first(),
            lambda: ServicioNivel1(codigo=codigo),
            CAMPOS_N1,
            nuevos,
            self._estado(destino_obs),
        )
        for obs in destino_obs:
            obs["n1"] = registro
        self._origen(
            "servicio_nivel1",
            registro,
            leido.filas,
            leido.rangos,
            valores,
            transformaciones,
            accion,
        )
        return registro

    # ------------------------------------------------------------------ nivel 2

    def _nivel2(self, leido):
        codigo = leido.codigo
        v = leido.valores
        obs_servicio = []
        transformaciones = []
        valores = {letra: celda.como_dict() for letra, celda in v.items()}

        def observar(tipo, detalle, **extra):
            obs_servicio.append(
                self._observar(
                    tipo, detalle, extra.pop("filas", [leido.fila]), codigo=codigo, **extra
                )
            )

        for letra, rango in leido.combinadas.items():
            transformaciones.append(
                {"campo": lector.ENCABEZADOS[letra], "regla": f"valor_de_celda_principal {rango}"}
            )

        # Nivel 1: celda A efectiva (dentro de su rango) o, si está vacía, por prefijo (D4).
        codigo_n1 = v["A"].valor
        if lector.vacio(codigo_n1):
            prefijo = ".".join(codigo.split(".")[:2]) if codigo.count(".") >= 2 else None
            nivel1 = self.nivel1.get(prefijo) if prefijo else None
            if nivel1 is None:
                raise ErrorImportacion(
                    f"El servicio {codigo} (fila {leido.fila}) no tiene nivel 1 en la columna A "
                    "y su prefijo no corresponde a ningún nivel 1 del archivo."
                )
            transformaciones.append({"campo": "nivel1", "regla": f"padre_por_prefijo {prefijo}"})
            observar(
                TipoObservacion.PADRE_POR_PREFIJO,
                f"A{leido.fila} está vacía y fuera de combinación; el nivel 1 {prefijo} se asigna "
                "por el prefijo del código.",
                celdas=[f"A{leido.fila}"],
                valores={"codigo": codigo, "prefijo": prefijo},
                regla="D4: padre por prefijo solo si A está vacía y el nivel 1 existe",
            )
        else:
            nivel1 = self.nivel1[lector._texto_codigo(codigo_n1)]

        if not lector.RE_COD_N2.match(codigo):
            observar(
                TipoObservacion.CODIGO_FORMATO_NO_ESTANDAR,
                f"El código «{codigo}» no sigue el formato SE.NN.NN; se conserva como texto sin "
                "normalizar.",
                celdas=[v["C"].celda],
                valores={v["C"].celda: codigo},
                regla="D5: códigos sin normalizar (codigo = codigo_original)",
            )

        # E: texto original; S/N reconocidos; vacío → NULL (D8).
        activo_excel = v["E"].valor
        if lector.vacio(activo_excel):
            activo_excel = None
        else:
            if not isinstance(activo_excel, str):
                activo_excel = str(activo_excel)
            if activo_excel not in ACTIVO_EXCEL_RECONOCIDOS:
                observar(
                    TipoObservacion.VALOR_NO_RECONOCIDO,
                    f"ACTIVO = «{activo_excel}» ({v['E'].celda}) no es S ni N; se conserva tal "
                    "cual.",
                    celdas=[v["E"].celda],
                    valores={"columna": "E", "fila": leido.fila, "valor": v["E"].valor},
                    regla="D8 (ajuste 2): activo_excel conserva el texto original",
                )

        # F, G, H: coincidencia exacta con etiqueta_original; sin coincidencia → NULL (§3.3).
        referencias = {}
        for nombre, (_, letra, _) in CATALOGOS.items():
            celda = v[letra]
            if lector.vacio(celda.valor):
                referencias[nombre] = None
                continue
            valor = self.catalogos[nombre].get(celda.valor)
            referencias[nombre] = valor
            if valor is None:
                transformaciones.append({"campo": nombre, "regla": "valor_no_reconocido_a_null"})
                observar(
                    TipoObservacion.VALOR_NO_RECONOCIDO,
                    f"«{celda.valor}» ({celda.celda}) no coincide exactamente con ninguna "
                    f"etiqueta del catálogo de {nombre}; queda sin valor y no se crea en el "
                    "catálogo.",
                    celdas=[celda.celda],
                    valores={"columna": letra, "fila": leido.fila, "valor": celda.valor},
                    regla="Regla de valores fuera de lista (modelo-datos.md §3.3)",
                )

        ausentes = [letra for letra in COLUMNAS_ESPERADAS if lector.vacio(v[letra].valor)]
        if ausentes:
            observar(
                TipoObservacion.ATRIBUTOS_AUSENTES,
                "Sin dato en el Excel: "
                + ", ".join(f"{COLUMNAS_ESPERADAS[c]} ({c})" for c in ausentes)
                + ". Se guardan como desconocidos (NULL), sin inventar valores.",
                celdas=[v[c].celda for c in ausentes],
                valores={"columnas": ausentes},
                regla="D6: ausencia → NULL + PENDIENTE_REVISION",
            )

        # K, L: número → Decimal; vacío → NULL (nunca 0); otro valor → NULL + observación.
        numeros = {}
        for campo, letra in (("minimo", "K"), ("maximo", "L")):
            celda = v[letra]
            numeros[campo] = _decimal(celda.valor)
            if lector.vacio(celda.valor):
                continue
            if numeros[campo] is None:
                observar(
                    TipoObservacion.VALOR_NO_RECONOCIDO,
                    f"{lector.ENCABEZADOS[letra]} = «{celda.valor}» ({celda.celda}) no es un "
                    "número; queda sin dato.",
                    celdas=[celda.celda],
                    valores={"columna": letra, "fila": leido.fila, "valor": celda.valor},
                    regla="K/L: solo valores numéricos; nunca se convierte a 0",
                )
            else:
                transformaciones.append({"campo": campo, "regla": "numero_a_decimal"})
        if (
            numeros["minimo"] is not None
            and numeros["maximo"] is not None
            and numeros["minimo"] > numeros["maximo"]
        ):
            observar(
                TipoObservacion.CONFLICTO_ATRIBUTOS,
                f"Mínimo ({numeros['minimo']}) mayor que máximo ({numeros['maximo']}); no se "
                "guardan esos valores.",
                celdas=[v["K"].celda, v["L"].celda],
                valores={"K": v["K"].valor, "L": v["L"].valor},
                regla="Regla §4.6: mínimo ≤ máximo; originales en valores_originales",
                severidad=Severidad.ERROR,
            )
            numeros = {"minimo": None, "maximo": None}

        self._continuacion(leido, valores, observar)

        descripcion = _texto_opcional(v["I"].valor)
        metrica = _texto_opcional(v["J"].valor)
        nuevos = {
            "nivel1_id": nivel1.pk,
            "nombre": v["D"].valor,
            "activo_excel": activo_excel,
            "clase_id": referencias["clase"].pk if referencias["clase"] else None,
            "criticidad_id": referencias["criticidad"].pk if referencias["criticidad"] else None,
            "tipo_id": referencias["tipo"].pk if referencias["tipo"] else None,
            "descripcion": descripcion,
            "metrica": metrica,
            **numeros,
        }
        for campo, letra in (
            ("activo_excel", "E"),
            ("clase", "F"),
            ("criticidad", "G"),
            ("tipo", "H"),
            ("descripcion", "I"),
            ("metrica", "J"),
            ("minimo", "K"),
            ("maximo", "L"),
        ):
            if lector.vacio(v[letra].valor) or (
                campo in ("descripcion", "metrica") and nuevos[campo] is None
            ):
                transformaciones.append({"campo": campo, "regla": "vacio_a_null"})

        antes = len(self.observaciones)
        self._observar_textos(codigo, [v["D"], v["I"], v["J"]], {})
        obs_servicio += self.observaciones[antes:]

        existente = ServicioNivel2.objects.filter(codigo_original=codigo).first()
        inactivas = {"nivel1": nivel1} if not nivel1.activo else {}
        inactivas.update(
            {n: ref for n, ref in referencias.items() if ref is not None and not ref.activo}
        )
        for campo, ref in inactivas.items():
            letra = COLUMNA_REFERENCIA[campo]
            celda = v[letra].celda if campo != "nivel1" else f"{letra}{leido.fila}"
            valor = v[letra].valor if not lector.vacio(v[letra].valor) else ref.codigo
            if existente is not None:
                efecto = "el servicio conserva sus valores actuales y no se le aplica ningún cambio"
            elif campo == "nivel1":
                efecto = "el servicio nuevo no se crea"
            else:
                efecto = f"el servicio nuevo se crea sin {campo}"
            observar(
                TipoObservacion.REFERENCIA_INACTIVA,
                f"«{valor}» ({celda}, {campo}) está dado de baja; {efecto}.",
                celdas=[celda],
                valores={"columna": letra, "fila": leido.fila, "valor": valor, "campo": campo},
                regla="Una referencia inactiva no se aplica ni aborta la importación",
            )
        if inactivas and existente is not None:
            self.resultado.conteos["nivel2"]["observados"] += 1
            registro, accion = existente, AccionOrigen.OBSERVADO
        elif "nivel1" in inactivas:
            self.resultado.filas["referencia_inactiva"].append(leido.fila)
            return
        else:
            for campo in inactivas:
                nuevos[f"{campo}_id"] = None
                transformaciones.append({"campo": campo, "regla": "referencia_inactiva_a_null"})
            registro, accion = self._upsert(
                "nivel2",
                existente,
                lambda: ServicioNivel2(codigo=codigo, codigo_original=codigo),
                CAMPOS_N2,
                nuevos,
                self._estado(obs_servicio),
            )
        for obs in obs_servicio:
            obs["n2"] = registro
        self._origen(
            "servicio_nivel2",
            registro,
            leido.filas,
            leido.rangos,
            valores,
            transformaciones,
            accion,
        )

    def _continuacion(self, leido, valores, observar):
        """Columnas no combinadas en filas de continuación: el valor de la fila principal
        prevalece. Una ausencia se informa (INFO); un valor distinto es un conflicto."""
        ausencias, conflictos = {}, {}
        for letra, otras in leido.continuacion.items():
            principal = leido.valores[letra].valor
            for fila, valor in otras.items():
                if lector.vacio(valor):
                    if not lector.vacio(principal):
                        ausencias.setdefault(letra, []).append(fila)
                elif valor != principal:
                    conflictos[f"{letra}{fila}"] = valor
                    valores[f"{letra} ({letra}{fila})"] = {
                        "celda": f"{letra}{fila}",
                        "valor": valor,
                    }
        if ausencias:
            observar(
                TipoObservacion.AUSENCIA_EN_CONTINUACION,
                "Columnas con valor solo en la fila principal: "
                + "; ".join(f"{c} vacía en filas {fs}" for c, fs in ausencias.items())
                + ". Se usa el valor de la fila principal.",
                filas=leido.filas,
                celdas=[f"{c}{f}" for c, fs in ausencias.items() for f in fs],
                valores={c: leido.valores[c].valor for c in ausencias},
                regla="Columnas I, K, L: valor de la fila principal del servicio",
            )
        if conflictos:
            observar(
                TipoObservacion.CONFLICTO_ATRIBUTOS,
                "Filas de continuación con valores distintos a la fila principal; prevalece la "
                "fila principal y los demás se conservan en los valores originales.",
                filas=leido.filas,
                celdas=list(conflictos),
                valores={
                    "principal": {c[0]: leido.valores[c[0]].valor for c in conflictos},
                    "continuacion": conflictos,
                },
                regla="Enunciado §3.4.6: prevalece el valor de la fila principal",
            )

    def _fila_sin_codigo(self, omitida):
        """D2: la fila no crea servicio ni se asigna a otro; sus valores quedan como evidencia."""
        fila = omitida.fila
        valores = {letra: omitida.valores[letra] for letra in "EFGH"}
        self._observar(
            TipoObservacion.FILA_SIN_CODIGO,
            f"La fila {fila} tiene datos pero C está vacía y fuera de combinación; no crea "
            "servicio ni se asigna a otro.",
            [fila],
            celdas=[f"C{fila}"],
            valores={"A (efectivo)": omitida.valores["A"], **valores},
            regla="D2: se omite y se registra la observación",
        )

    def _controles(self):
        r = self.resultado
        for nivel, obtenido, esperado in (
            ("nivel 1", r.total_n1, ESPERADO_N1),
            ("nivel 2", r.total_n2, ESPERADO_N2),
        ):
            pasa = obtenido == esperado
            informativo = "" if pasa or r.controles_exigidos else " (informativo)"
            self._observar(
                TipoObservacion.CONTROL_CONTEO,
                f"Registros de {nivel} con código del archivo: {obtenido}, esperados {esperado} → "
                f"{'PASA' if pasa else 'FALLA'}{informativo}.",
                [lector.FILA_INI, lector.FILA_FIN],
                valores={"nivel": nivel, "esperado": esperado, "obtenido": obtenido},
                regla="Enunciado §3.4: 12 códigos de nivel 1 y 46 de nivel 2",
                severidad=Severidad.INFO
                if pasa
                else (Severidad.ERROR if r.controles_exigidos else Severidad.ADVERTENCIA),
            )

    # ------------------------------------------------------------------ escritura

    @staticmethod
    def _estado(observaciones):
        if any(o["severidad"] in REQUIEREN_REVISION for o in observaciones):
            return EstadoRevision.PENDIENTE_REVISION
        return EstadoRevision.SIN_OBSERVACIONES

    def _upsert(self, entidad, registro, nuevo, campos, nuevos, estado):
        """Crea o actualiza solo los campos del Excel. `estado_revision = REVISADO` puesto por un
        administrador se respeta (S7). Toda escritura pasa por `full_clean()` (D9)."""
        conteo = self.resultado.conteos[entidad]
        if registro is None:
            registro, accion = nuevo(), AccionOrigen.CREADO
        else:
            accion = AccionOrigen.SIN_CAMBIOS
        if registro.estado_revision != EstadoRevision.REVISADO:
            nuevos = {**nuevos, "estado_revision": estado}
            campos = (*campos, "estado_revision")
        if accion == AccionOrigen.SIN_CAMBIOS and _hay_cambios(registro, campos, nuevos):
            accion = AccionOrigen.ACTUALIZADO
        if accion != AccionOrigen.SIN_CAMBIOS:
            for campo in campos:
                setattr(registro, campo, nuevos[campo])
            if isinstance(registro, ServicioNivel2):
                guardar_servicio_nivel2(registro)
            else:
                registro.full_clean()
                registro.save()
        conteo[CLAVE_CONTEO[accion]] += 1
        return registro, accion

    def _origen(self, campo, registro, filas, rangos, valores, transformaciones, accion):
        datos = {
            "hoja": lector.HOJA,
            "filas": filas,
            "rangos_combinados": rangos,
            "valores_originales": _a_json(valores),
            "transformaciones": transformaciones,
            "ultima_ejecucion": self.ejecucion,
            "ultima_accion": accion,
        }
        origen = OrigenServicio.objects.filter(**{campo: registro}).first()
        if origen is None:
            OrigenServicio.objects.create(
                **{campo: registro}, primera_ejecucion=self.ejecucion, **datos
            )
            return
        for clave, dato in datos.items():
            setattr(origen, clave, dato)
        origen.save()
