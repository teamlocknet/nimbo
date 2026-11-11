"""nimbo-tor — enciende y apaga el modo Tor (ADR-012 aceptado, #45).

  nimbo-tor on      arranca nimbo-modo-tor.service: tabla nftables -> tor -> vigilante
  nimbo-tor off     la para en orden inverso: vigilante -> tor -> tabla
  nimbo-tor estado  dice si el modo está activo

nimbo-tor NO corre como root: solo pide a systemd que arranque o pare la unidad, y
systemd pide la autorización (polkit). La red la levanta antes `nimbo-red on` (ADR-019).
Tor no arranca solo: en reposo no hay ni conexiones ni puertos (RNF-01).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Callable

UNIDAD = "nimbo-modo-tor.service"

Ejecutor = Callable[[list[str]], str]


def ejecutar_sistema(argv: list[str]) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def _detalle(e: subprocess.CalledProcessError) -> str:
    return (e.stderr or "").strip() or f"código {e.returncode}"


def encender(ejecutar: Ejecutor) -> int:
    try:
        ejecutar(["systemctl", "start", UNIDAD])
    except subprocess.CalledProcessError as e:
        print(f"nimbo-tor: no se pudo activar el modo Tor ({_detalle(e)}).\n"
              f"Si la tabla llegó a cargarse, la red sigue cerrada: es lo seguro.\n"
              f"Detalle: journalctl -u nimbo-modo-tor -b · Para salir: nimbo-tor off")
        return 1
    print("nimbo-tor: modo Tor ACTIVO. Abre \"Navegar por Tor\" o ejecuta: nimbo-navegar-tor\n"
          "Mientras esté activo, solo tor puede salir a la red.")
    return 0


def apagar(ejecutar: Ejecutor) -> int:
    try:
        ejecutar(["systemctl", "stop", UNIDAD])
    except subprocess.CalledProcessError as e:
        print(f"nimbo-tor: no se pudo apagar el modo Tor del todo ({_detalle(e)}).\n"
              "La red sigue cerrada (lo seguro). Revisa: journalctl -u nimbo-modo-tor -b\n"
              "Para abrirla a mano, con sudo: systemctl stop tor@default.service && "
              "nft delete table inet nimbo_tor")
        return 1
    print("nimbo-tor: modo Tor APAGADO. Red normal restaurada.")
    return 0


def estado(ejecutar: Ejecutor) -> int:
    try:
        activo = ejecutar(["systemctl", "is-active", UNIDAD]).strip() == "active"
    except subprocess.CalledProcessError:
        activo = False
    print("nimbo-tor: modo Tor activo" if activo else "nimbo-tor: modo Tor inactivo")
    return 0


def main(argv: list[str] | None = None, ejecutar: Ejecutor = ejecutar_sistema) -> int:
    p = argparse.ArgumentParser(prog="nimbo-tor", description=__doc__.splitlines()[0])
    p.add_argument("accion", choices=["on", "off", "estado"])
    args = p.parse_args(sys.argv[1:] if argv is None else argv)
    return {"on": encender, "off": apagar, "estado": estado}[args.accion](ejecutar)


if __name__ == "__main__":
    sys.exit(main())
