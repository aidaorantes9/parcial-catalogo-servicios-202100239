"""Importa el catálogo desde el Excel original (enunciado §3.4).

Uso: python manage.py importar_catalogo [--archivo RUTA] [--sha256 RUTA] [--exigir-controles]
                                          [--dry-run]

Con el archivo original verifica el SHA-256 antes de leer y exige los controles 12 (nivel 1) / 46
(nivel 2): si algo falla, aborta con código distinto de 0. Con otro archivo registra su SHA-256,
avisa que no es el original y solo informa los controles, salvo --exigir-controles.
"""

from django.core.management.base import BaseCommand, CommandError

from importacion import importador
from importacion.models import TipoObservacion

ETIQUETAS_ENTIDAD = {
    "clase": "Clases de servicio",
    "criticidad": "Criticidades",
    "tipo": "Tipos de servicio",
    "nivel1": "Servicios de nivel 1",
    "nivel2": "Servicios de nivel 2",
}
ETIQUETAS_FILAS = {
    "servicio": "servicios de nivel 2",
    "continuacion": "filas de continuación (omitidas)",
    "sin_codigo": "filas sin código fuera de combinación (omitidas)",
    "vacia": "filas vacías (omitidas)",
    "referencia_inactiva": "servicios nuevos no creados: nivel 1 inactivo (omitidos)",
}


class Command(BaseCommand):
    help = (
        "Importa el catálogo de servicios desde el Excel original. Repetible: no duplica "
        "registros ni observaciones."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--archivo",
            default=importador.ARCHIVO_POR_DEFECTO,
            help=f"Libro a importar (por defecto {importador.ARCHIVO_POR_DEFECTO}, montado en "
            "solo lectura).",
        )
        parser.add_argument(
            "--sha256",
            default=None,
            help="Archivo con la suma SHA-256 esperada, formato sha256sum. Con el archivo "
            f"original, por defecto {importador.SHA256_POR_DEFECTO}; con otro archivo solo se "
            "verifica si se indica.",
        )
        parser.add_argument(
            "--exigir-controles",
            action="store_true",
            help="Con un archivo distinto del original, falla si los controles 12/46 no pasan "
            "(con el original siempre se exigen).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Ejecuta todo y revierte al final: no queda nada guardado.",
        )

    def handle(self, *args, archivo, sha256, dry_run, exigir_controles, **options):
        try:
            resultado = importador.importar(
                archivo, sha256, dry_run=dry_run, exigir_controles=exigir_controles
            )
        except importador.ErrorImportacion as error:
            if error.resultado is not None:
                self._resumen(error.resultado)
            raise CommandError(f"Importación abortada: {error}") from error
        self._resumen(resultado)

    def _resumen(self, r):
        w = self.stdout.write
        w("== Resumen de importación ==")
        w(f"Archivo: {r.archivo}")
        w(f"SHA-256: {r.sha256}")
        if not r.es_original:
            w(
                self.style.WARNING(
                    f"AVISO: {r.archivo} no es el archivo original "
                    f"({importador.ARCHIVO_POR_DEFECTO}). Su SHA-256 se registra en la ejecución"
                    " y los controles 12/46 "
                    + (
                        "se exigen (--exigir-controles)."
                        if r.controles_exigidos
                        else "solo se informan (use --exigir-controles para que fallen)."
                    )
                )
            )
        if r.dry_run:
            w(self.style.WARNING("Modo --dry-run: todos los cambios se revirtieron."))
        estado = r.estado + (f" (ejecución #{r.ejecucion_id})" if r.ejecucion_id else "")
        w(f"Estado: {estado}")
        if r.mensaje_error:
            w(self.style.ERROR(f"Error: {r.mensaje_error}"))
        if r.filas:
            w("")
            w("Filas 5–101:")
            for motivo, filas in r.filas.items():
                detalle = f" → {filas}" if motivo != "servicio" and filas else ""
                w(f"  {len(filas):>3} {ETIQUETAS_FILAS[motivo]}{detalle}")
        if r.filas:
            w("")
            if r.estado == "FALLIDA":
                w("Conteos calculados antes del fallo (la transacción se revirtió):")
            w(f"{'Entidad':<24}{'Creados':>9}{'Actualiz.':>11}{'Sin camb.':>11}{'Observ.':>9}")
            filas_tabla = [(ETIQUETAS_ENTIDAD[e], c) for e, c in r.conteos.items()]
            filas_tabla.append(("TOTAL", {a: r.total(a) for a in importador.ACCIONES_CONTEO}))
            for etiqueta, c in filas_tabla:
                w(
                    f"{etiqueta:<24}{c['creados']:>9}{c['actualizados']:>11}"
                    f"{c['sin_cambios']:>11}{c['observados']:>9}"
                )
            w("")
            w(
                f"Creados: {r.total('creados')} · Actualizados: {r.total('actualizados')} · "
                f"Sin cambios: {r.total('sin_cambios')} · Omitidos: {r.omitidos} · "
                f"Observados: {len(r.observaciones)} "
                f"({sum(1 for o in r.observaciones if o['nueva'])} nuevas)"
            )
            w(
                f"Registros observados (referencia inactiva, sin cambios aplicados): "
                f"{r.total('observados')}"
            )
        if r.observaciones:
            w("")
            w("Observaciones por tipo (emitidas en esta ejecución / nuevas):")
            nuevas = {}
            for o in r.observaciones:
                nuevas[o["tipo"]] = nuevas.get(o["tipo"], 0) + (1 if o["nueva"] else 0)
            for tipo, total in r.por_tipo().items():
                w(f"  {tipo:<32}{total:>3} / {nuevas[tipo]}  {TipoObservacion(tipo).label}")
            w("")
            w("Detalle de observaciones con advertencia o error:")
            for o in r.observaciones:
                if o["severidad"] == "INFO":
                    continue
                codigo = o["codigo_afectado"] or "sin código"
                w(f"  [{o['severidad']}] {o['tipo']} · {codigo} · filas {o['filas']}:")
                w(f"      {o['detalle']}")
        if r.total_n1 is not None:
            w("")
            w("Controles:")
            for nombre, obtenido, esperado, pasa in (
                ("Códigos de nivel 1", r.total_n1, importador.ESPERADO_N1, r.control_n1),
                ("Códigos de nivel 2", r.total_n2, importador.ESPERADO_N2, r.control_n2),
            ):
                if pasa:
                    marca = self.style.SUCCESS("PASA")
                elif r.controles_exigidos:
                    marca = self.style.ERROR("FALLA")
                else:
                    marca = self.style.WARNING("FALLA (informativo: no es el archivo original)")
                w(f"  {nombre}: {obtenido} / esperado {esperado} → {marca}")
