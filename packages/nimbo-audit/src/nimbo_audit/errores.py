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
