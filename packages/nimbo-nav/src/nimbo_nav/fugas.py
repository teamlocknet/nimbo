"""Lógica pura de detección de fugas del modo Tor (ADR-012, RF-NAV-02).

Dos fuentes, ninguna basta sola:
  * el contador "fugas" de la tabla nftables: paquetes que algo intentó sacar fuera de
    tor y que la tabla descartó (la protección funcionó, pero hubo un intento);
  * los sockets del sistema (`ss -Htunp`): conexiones no-loopback de un proceso que no es
    tor (detecta también una fuga si la tabla faltara o estuviera mal).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

LOOPBACK = ("127.", "[::1]", "::1")


@dataclass(frozen=True)
class Conexion:
    protocolo: str
    estado: str
    local: str
    remota: str
    proceso: str


@dataclass(frozen=True)
class Resultado:
    paquetes_descartados: int
    conexiones: list[Conexion] = field(default_factory=list)

    @property
    def limpio(self) -> bool:
        return self.paquetes_descartados == 0 and not self.conexiones


def leer_contador(json_nft: str, nombre: str = "fugas") -> int:
    """Paquetes del contador `nombre` en la salida de `nft -j list counter ...`."""
    datos = json.loads(json_nft)
    for objeto in datos.get("nftables", []):
        contador = objeto.get("counter")
        if contador and contador.get("name") == nombre:
            return int(contador["packets"])
    raise ValueError(f"no se encontró el contador {nombre!r}")


_PROCESO = re.compile(r'users:\(\("([^"]+)"')


def _es_loopback(direccion: str) -> bool:
    return direccion.startswith(LOOPBACK)


def conexiones_fuera_de_tor(salida_ss: str) -> list[Conexion]:
    """Conexiones no-loopback de procesos que no son tor, en la salida de `ss -Htunp`."""
    fugas = []
    for linea in salida_ss.splitlines():
        campos = linea.split()
        if len(campos) < 6:
            continue
        protocolo, estado, local, remota = campos[0], campos[1], campos[4], campos[5]
        if estado in ("LISTEN", "UNCONN"):
            continue
        if _es_loopback(local) and _es_loopback(remota):
            continue
        m = _PROCESO.search(linea)
        proceso = m.group(1) if m else "desconocido"
        if proceso == "tor":
            continue
        fugas.append(Conexion(protocolo, estado, local, remota, proceso))
    return fugas


def evaluar(paquetes_descartados: int, conexiones: list[Conexion]) -> Resultado:
    return Resultado(paquetes_descartados, list(conexiones))
