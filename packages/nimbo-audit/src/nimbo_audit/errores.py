"""Excepciones propias del CLI.

Objetivo: nunca mostrar un traceback crudo al usuario. `cli.py` atrapa
`NimboAuditError` y sus subclases y las traduce a un mensaje `[ERROR] ...`
limpio con código de salida != 0 (degradación graciosa, RNF-08).
"""


class NimboAuditError(Exception):
    """Base de todos los errores esperados del CLI (los que sí se muestran limpios)."""


class NombreInvalidoError(NimboAuditError):
    """El nombre del engagement contiene caracteres no permitidos o es peligroso."""


class EngagementExistenteError(NimboAuditError):
    """Ya existe un engagement con ese identificador y no se pidió --force."""


class EngagementNoActivoError(NimboAuditError):
    """No se pudo determinar un engagement activo (ni por cwd ni por --dir)."""


class ArchivoNoAccesibleError(NimboAuditError):
    """El archivo de evidencia no existe o no es accesible (CU-02 3a)."""


class EvidenciaDuplicadaError(NimboAuditError):
    """Ya hay evidencia registrada con ese nombre: no se sobrescribe en silencio."""


class ExportacionPDFError(NimboAuditError):
    """La exportación a PDF no fue posible (pandoc ausente o sin motor PDF).

    Es una degradación graciosa: el CLI la traduce a un `[AVISO]` y el `.md`
    (entregable primario) SIEMPRE queda generado. Nunca revienta el flujo.
    """


class InterrupcionMemoriaError(NimboAuditError):
    """El cálculo del hash se interrumpió por restricción de memoria (RNF-08).

    Se traduce a un `[AVISO]` limpio; el archivo NO queda registrado y el estado
    del engagement permanece intacto.
    """
