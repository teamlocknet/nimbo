"""nimbo-tor — enciende y apaga el modo Tor (ADR-012, decisiones C1 y D2).

  sudo nimbo-tor on      carga la tabla nftables (falla cerrada) y DESPUÉS arranca tor
  sudo nimbo-tor off     para tor y el vigilante, y borra la tabla
  sudo nimbo-tor estado  dice si el modo está activo

Tor no arranca solo: en reposo no hay ni conexiones ni puertos (RNF-01).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Callable

TABLA_NFT = "/usr/share/nimbo-nav/nimbo-tor.nft"

Ejecutor = Callable[[list[str]], str]


def ejecutar_sistema(argv: list[str]) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def _root() -> bool:
    return os.geteuid() == 0


def encender(ejecutar: Ejecutor) -> int:
    try:
        # Primero la tabla: si no carga, tor no arranca (nunca hay tor sin protección).
        ejecutar(["nft", "-f", TABLA_NFT])
    except subprocess.CalledProcessError as e:
        print(f"nimbo-tor: no se pudo cargar la tabla nftables; tor NO se arranca.\n{e.stderr}")
        return 1
    try:
        ejecutar(["systemctl", "start", "tor@default.service"])
        ejecutar(["systemctl", "start", "nimbo-leakcheck.service"])
    except subprocess.CalledProcessError as e:
        print(f"nimbo-tor: fallo al arrancar tor ({e.stderr}). La tabla sigue cargada: "
              "la red sigue cerrada hasta 'sudo nimbo-tor off'.")
        return 1
    print("nimbo-tor: modo Tor ACTIVO. Abre el navegador con: nimbo-navegar-tor\n"
          "Mientras esté activo, solo tor puede salir a la red.")
    return 0


def apagar(ejecutar: Ejecutor) -> int:
    for argv in (["systemctl", "stop", "nimbo-leakcheck.service"],
                 ["systemctl", "stop", "tor@default.service"]):
        ejecutar(argv)
    try:
        ejecutar(["nft", "delete", "table", "inet", "nimbo_tor"])
    except subprocess.CalledProcessError:
        pass  # ya estaba borrada
    print("nimbo-tor: modo Tor APAGADO. Red normal restaurada.")
    return 0


def estado(ejecutar: Ejecutor) -> int:
    try:
        ejecutar(["nft", "list", "table", "inet", "nimbo_tor"])
    except subprocess.CalledProcessError:
        print("nimbo-tor: modo Tor inactivo")
        return 0
    print("nimbo-tor: modo Tor activo")
    return 0


def main(argv: list[str] | None = None, ejecutar: Ejecutor = ejecutar_sistema,
         es_root: Callable[[], bool] = _root) -> int:
    p = argparse.ArgumentParser(prog="nimbo-tor", description=__doc__.splitlines()[0])
    p.add_argument("accion", choices=["on", "off", "estado"])
    args = p.parse_args(sys.argv[1:] if argv is None else argv)
    if not es_root():
        print(f"nimbo-tor: necesita privilegios. Usa: sudo nimbo-tor {args.accion}")
        return 2
    return {"on": encender, "off": apagar, "estado": estado}[args.accion](ejecutar)


if __name__ == "__main__":
    sys.exit(main())
