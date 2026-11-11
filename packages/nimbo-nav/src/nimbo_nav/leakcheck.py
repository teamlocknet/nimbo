"""nimbo-leakcheck — comprueba que, con el modo Tor activo, nada sale fuera del túnel.

Códigos de salida:
  0  modo Tor activo y sin fugas
  1  FUGA: paquetes descartados por la tabla o conexiones directas de otros procesos
  2  el modo Tor no está activo
  3  no se pudo comprobar (falló `ss` u otra herramienta): NO se da por limpio

Necesita root para leer el contador de nftables. Con --vigilar lo arranca
nimbo-leakcheck.service y deja el estado en /run/nimbo-nav/leakcheck.json, que
nimbo-navegar-tor lee para avisar al usuario. Un fallo en una vuelta NO detiene el
vigilante: se escribe "vigilante": "error" y se reintenta en la siguiente.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from .fugas import Resultado, conexiones_fuera_de_tor, evaluar, leer_contador

RUTA_ESTADO = "/run/nimbo-nav/leakcheck.json"
CMD_CONTADOR = ["nft", "-j", "list", "counter", "inet", "nimbo_tor", "fugas"]
CMD_SOCKETS = ["ss", "-Htunp"]

Ejecutor = Callable[[list[str]], str]


class NoSePudoComprobar(Exception):
    """Falló una herramienta: el resultado es desconocido, nunca 'limpio'."""


def ejecutar_sistema(argv: list[str]) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def comprobar(ejecutar: Ejecutor) -> Resultado | None:
    """Resultado, o None si el modo Tor no está activo (no existe la tabla).

    Lanza NoSePudoComprobar si la tabla existe pero no se pueden leer los sockets.
    """
    try:
        paquetes = leer_contador(ejecutar(CMD_CONTADOR))
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None
    try:
        salida_ss = ejecutar(CMD_SOCKETS)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        raise NoSePudoComprobar(f"ss falló: {e}") from e
    return evaluar(paquetes, conexiones_fuera_de_tor(salida_ss))


def estado_json(resultado: Resultado | None, ahora: float) -> dict:
    if resultado is None:
        return {"modo_tor": False, "vigilante": "ok", "actualizado": ahora, "limpio": None,
                "paquetes_descartados": 0, "conexiones": []}
    return {
        "modo_tor": True,
        "vigilante": "ok",
        "actualizado": ahora,
        "limpio": resultado.limpio,
        "paquetes_descartados": resultado.paquetes_descartados,
        "conexiones": [asdict(c) for c in resultado.conexiones],
    }


def estado_error(error: str, ahora: float) -> dict:
    return {"modo_tor": True, "vigilante": "error", "error": error, "actualizado": ahora,
            "limpio": None, "paquetes_descartados": 0, "conexiones": []}


def escribir_estado(ruta: Path, datos: dict) -> None:
    """Escritura atómica (rename) para que el lector nunca vea un JSON a medias."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=".leakcheck.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    os.chmod(tmp, 0o644)
    os.replace(tmp, ruta)


def vuelta_vigilante(ruta: Path, ejecutar: Ejecutor, ahora: Callable[[], float] = time.time) -> dict:
    """Una comprobación del vigilante. Nunca lanza: cualquier fallo queda en el estado."""
    try:
        datos = estado_json(comprobar(ejecutar), ahora())
    except Exception as e:  # noqa: BLE001 — el vigilante no puede morir en silencio
        datos = estado_error(str(e), ahora())
    escribir_estado(Path(ruta), datos)
    return datos


def informar(resultado: Resultado | None) -> int:
    if resultado is None:
        print("nimbo-leakcheck: el modo Tor no está activo (actívalo con: nimbo-tor on)")
        return 2
    if resultado.limpio:
        print("nimbo-leakcheck: OK — 0 fugas (modo Tor activo)")
        return 0
    print("nimbo-leakcheck: FUGA detectada")
    if resultado.paquetes_descartados:
        print(f"  - {resultado.paquetes_descartados} paquetes intentaron salir fuera de Tor "
              "(la tabla los descartó; ver: journalctl -k | grep nimbo-fuga)")
    for c in resultado.conexiones:
        print(f"  - {c.proceso}: {c.protocolo} {c.estado} {c.local} -> {c.remota}")
    return 1


def main(argv: list[str] | None = None, ejecutar: Ejecutor = ejecutar_sistema,
         dormir: Callable[[float], None] = time.sleep) -> int:
    p = argparse.ArgumentParser(prog="nimbo-leakcheck", description=__doc__.splitlines()[0])
    p.add_argument("--estado", help="escribe el resultado en este fichero JSON")
    p.add_argument("--vigilar", action="store_true",
                   help=f"repite la comprobación sin parar y escribe {RUTA_ESTADO}")
    p.add_argument("--intervalo", type=float, default=2.0, help="segundos entre comprobaciones")
    args = p.parse_args(sys.argv[1:] if argv is None else argv)

    if args.vigilar:
        ruta = Path(args.estado or RUTA_ESTADO)
        while True:
            vuelta_vigilante(ruta, ejecutar)
            dormir(args.intervalo)

    try:
        resultado = comprobar(ejecutar)
    except NoSePudoComprobar as e:
        if args.estado:
            escribir_estado(Path(args.estado), estado_error(str(e), time.time()))
        print(f"nimbo-leakcheck: ERROR — no se pudo comprobar ({e}). No se da por limpio.")
        return 3
    if args.estado:
        escribir_estado(Path(args.estado), estado_json(resultado, time.time()))
    return informar(resultado)


if __name__ == "__main__":
    sys.exit(main())
