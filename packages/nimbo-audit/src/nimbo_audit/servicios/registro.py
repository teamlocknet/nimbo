"""Registro de custodia del caso (ADR-021): quién hizo qué, encadenado por hash.

Cada línea de `custodia/registro.jsonl` guarda el hash de la anterior, así que
editar, borrar o reordenar una entrada rompe la cadena. La cadena sola NO impide
que alguien la recalcule entera: eso lo cierra el sello (`servicios/sello.py`).
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from nimbo_audit.errores import RegistroError
from nimbo_audit.modelos.evidencia import Evidencia

CUSTODIA = "custodia"
RUTA_REGISTRO = f"{CUSTODIA}/registro.jsonl"
RUTA_SELLO = f"{CUSTODIA}/sello.json"
RUTA_FIRMA = f"{CUSTODIA}/sello.json.asc"
RUTA_CLAVE = f"{CUSTODIA}/clave-publica.asc"
RUTAS_SELLO = (RUTA_SELLO, RUTA_FIRMA, RUTA_CLAVE)
GENESIS = "0" * 64

VALIDO = "VALIDO"
ROTO = "ROTO"
SIN_REGISTRO = "SIN REGISTRO"


@dataclass(frozen=True)
class EstadoRegistro:
    estado: str
    entradas: int = 0
    detalle: str = ""


def caso_sellado(raiz: Path) -> bool:
    """Cualquier pieza del sello marca el caso como cerrado a cambios."""
    return any(os.path.lexists(Path(raiz) / ruta) for ruta in RUTAS_SELLO)


def _hash_entrada(entrada: dict[str, Any]) -> str:
    sin_hash = {k: v for k, v in entrada.items() if k != "hash"}
    canonico = json.dumps(sin_hash, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _validar_cadena(texto: str) -> list[dict[str, Any]]:
    if texto and not texto.endswith("\n"):
        raise RegistroError("la última línea está incompleta")
    entradas: list[dict[str, Any]] = []
    previo = GENESIS
    for seq, linea in enumerate(texto.splitlines(), start=1):
        try:
            entrada = json.loads(linea)
        except ValueError as exc:
            raise RegistroError(f"la línea {seq} no es válida") from exc
        if not isinstance(entrada, dict) or not isinstance(entrada.get("accion"), str):
            raise RegistroError(f"la línea {seq} no es válida")
        if entrada.get("seq") != seq or entrada.get("previo") != previo:
            raise RegistroError(f"la cadena se rompe en la línea {seq}")
        if entrada.get("hash") != _hash_entrada(entrada):
            raise RegistroError(f"la línea {seq} fue alterada")
        previo = entrada["hash"]
        entradas.append(entrada)
    return entradas


def evidencias_del_registro(entradas: Iterable[dict[str, Any]]) -> dict[str, str]:
    """Nombre -> SHA-256 de cada evidencia según el registro."""
    evidencias: dict[str, str] = {}
    for entrada in entradas:
        if entrada["accion"] == "adopcion":
            nuevas = entrada.get("evidencias")
            if not isinstance(nuevas, dict):
                raise RegistroError(f"la línea {entrada['seq']} no es válida")
        elif entrada["accion"] == "capture":
            nuevas = {entrada.get("nombre"): entrada.get("sha256")} if isinstance(
                entrada.get("nombre"), str
            ) else {None: None}
        else:
            continue
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in nuevas.items()):
            raise RegistroError(f"la línea {entrada['seq']} no es válida")
        evidencias.update(nuevas)
    return evidencias


class RegistroCustodia:
    """Registro de solo añadir de un caso."""

    def __init__(self, raiz: Path, *, ahora: datetime | None = None) -> None:
        self._archivo = Path(raiz) / RUTA_REGISTRO
        self._ahora = ahora

    def existe(self) -> bool:
        return os.path.lexists(self._archivo)

    def leer_validado(self) -> list[dict[str, Any]]:
        if self._archivo.is_symlink():
            raise RegistroError("el registro es un enlace simbólico")
        try:
            return _validar_cadena(self._archivo.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            raise RegistroError("no se pudo leer el registro") from exc

    def anadir(self, accion: str, analista: str, **detalle: Any) -> dict[str, Any]:
        """Añade una entrada. Se niega a prolongar una cadena rota."""
        try:
            self._archivo.parent.mkdir(parents=True, exist_ok=True)
            with open(self._archivo, "a+", encoding="utf-8") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                fh.seek(0)
                entradas = _validar_cadena(fh.read())
                entrada = {
                    **detalle,
                    "seq": len(entradas) + 1,
                    "previo": entradas[-1]["hash"] if entradas else GENESIS,
                    "accion": accion,
                    "analista": analista,
                    "timestamp": self._marca_temporal(),
                }
                entrada["hash"] = _hash_entrada(entrada)
                fh.write(json.dumps(entrada, ensure_ascii=False, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        except (OSError, UnicodeDecodeError) as exc:
            raise RegistroError(f"no se pudo escribir el registro: {exc}") from exc
        return entrada

    def adoptar_si_falta(self, evidencias: Iterable[Evidencia], analista: str) -> None:
        """Un caso de 0.1.0 entra en custodia declarando lo que ya tenía."""
        if not self.existe():
            self.anadir(
                "adopcion", analista,
                evidencias={e.nombre: e.sha256.lower() for e in evidencias},
            )

    def comprobar(self, evidencias: Iterable[Evidencia]) -> EstadoRegistro:
        if not self.existe():
            return EstadoRegistro(SIN_REGISTRO)
        try:
            entradas = self.leer_validado()
            registradas = evidencias_del_registro(entradas)
        except RegistroError as exc:
            return EstadoRegistro(ROTO, detalle=str(exc))
        indice = {e.nombre: e.sha256.lower() for e in evidencias}
        if registradas != indice:
            return EstadoRegistro(
                ROTO, len(entradas), "el índice no coincide con lo registrado"
            )
        return EstadoRegistro(VALIDO, len(entradas))

    def _marca_temporal(self) -> str:
        momento = self._ahora or datetime.now(timezone.utc)
        return momento.isoformat(timespec="seconds")
