"""nimbo-leakcheck — comprueba que, con el modo Tor activo, nada sale fuera del túnel.

Códigos de salida:
  0  modo Tor activo y sin fugas
  1  FUGA: paquetes descartados por la tabla o conexiones directas de otros procesos
  2  el modo Tor no está activo (o no se pudo leer el estado)

Necesita root para leer el contador de nftables. Con --vigilar lo arranca
nimbo-leakcheck.service y deja el estado en /run/nimbo-nav/leakcheck.json, que
nimbo-navegar-tor lee para avisar al usuario en el escritorio.
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


def ejecutar_sistema(argv: list[str]) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def comprobar(ejecutar: Ejecutor) -> Resultado | None:
    """Resultado de la comprobación, o None si el modo Tor no está activo."""
    try:
        paquetes = leer_contador(ejecutar(CMD_CONTADOR))
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None
    return evaluar(paquetes, conexiones_fuera_de_tor(ejecutar(CMD_SOCKETS)))


def estado_json(resultado: Resultado | None) -> dict:
    if resultado is None:
        return {"modo_tor": False, "limpio": None, "paquetes_descartados": 0, "conexiones": []}
    return {
        "modo_tor": True,
        "limpio": resultado.limpio,
        "paquetes_descartados": resultado.paquetes_descartados,
        "conexiones": [asdict(c) for c in resultado.conexiones],
    }


def escribir_estado(ruta: Path, datos: dict) -> None:
    """Escritura atómica (rename) para que el lector nunca vea un JSON a medias."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=".leakcheck.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    os.chmod(tmp, 0o644)
    os.replace(tmp, ruta)


def informar(resultado: Resultado | None) -> int:
    if resultado is None:
        print("nimbo-leakcheck: el modo Tor no está activo (ejecuta: sudo nimbo-tor on)")
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


def main(argv: list[str] | None = None, ejecutar: Ejecutor = ejecutar_sistema) -> int:
    p = argparse.ArgumentParser(prog="nimbo-leakcheck", description=__doc__.splitlines()[0])
    p.add_argument("--estado", help="escribe el resultado en este fichero JSON")
    p.add_argument("--vigilar", action="store_true",
                   help=f"repite la comprobación sin parar y escribe {RUTA_ESTADO}")
    p.add_argument("--intervalo", type=float, default=2.0, help="segundos entre comprobaciones")
    args = p.parse_args(sys.argv[1:] if argv is None else argv)

    if args.vigilar:
        ruta = Path(args.estado or RUTA_ESTADO)
        while True:
            escribir_estado(ruta, estado_json(comprobar(ejecutar)))
            time.sleep(args.intervalo)

    resultado = comprobar(ejecutar)
    if args.estado:
        escribir_estado(Path(args.estado), estado_json(resultado))
    return informar(resultado)


if __name__ == "__main__":
    sys.exit(main())
