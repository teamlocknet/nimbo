"""nimbo-navegar-tor — abre firefox-esr con el perfil Tor y avisa si hay fugas.

Se ejecuta como el usuario (sin sudo). Exige que el modo Tor esté activo
(`sudo nimbo-tor on`). Mientras el navegador está abierto, lee el estado que deja
nimbo-leakcheck y muestra una notificación de escritorio si aparece una fuga (HU-08 CA-3).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from .leakcheck import RUTA_ESTADO

PLANTILLA = Path("/usr/share/nimbo-nav/tor-user.js")
PERFIL = Path.home() / ".local" / "share" / "nimbo-nav" / "perfil-tor"


def leer_estado(ruta: Path) -> dict | None:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def debe_avisar(anterior: dict | None, actual: dict | None) -> bool:
    """Avisa cuando aumentan los paquetes descartados o las conexiones fuera de Tor."""
    if not actual or not actual.get("modo_tor"):
        return False
    previo_p = (anterior or {}).get("paquetes_descartados", 0)
    previo_c = len((anterior or {}).get("conexiones", []))
    return (actual.get("paquetes_descartados", 0) > previo_p
            or len(actual.get("conexiones", [])) > previo_c)


def preparar_perfil(perfil: Path, plantilla: Path) -> None:
    perfil.mkdir(parents=True, exist_ok=True)
    os.chmod(perfil, 0o700)
    shutil.copyfile(plantilla, perfil / "user.js")


def avisar(estado: dict) -> None:
    texto = (f"{estado.get('paquetes_descartados', 0)} paquetes bloqueados fuera de Tor; "
             f"{len(estado.get('conexiones', []))} conexiones directas. "
             "Detalle: sudo nimbo-leakcheck")
    subprocess.run(["notify-send", "--urgency=critical", "nimbo: posible FUGA fuera de Tor", texto],
                   check=False)
    print(f"nimbo-navegar-tor: AVISO — {texto}", file=sys.stderr)


def lanzar_firefox(perfil: Path) -> subprocess.Popen:
    return subprocess.Popen(["firefox-esr", "--no-remote", "--profile", str(perfil)])


def main(argv: list[str] | None = None, ruta_estado: Path = Path(RUTA_ESTADO),
         lanzar: Callable[[Path], object] = lanzar_firefox) -> int:
    p = argparse.ArgumentParser(prog="nimbo-navegar-tor", description=__doc__.splitlines()[0])
    p.add_argument("--perfil", type=Path, default=PERFIL)
    args = p.parse_args(sys.argv[1:] if argv is None else argv)

    estado = leer_estado(ruta_estado)
    if not estado or not estado.get("modo_tor"):
        print("nimbo-navegar-tor: el modo Tor no está activo. Primero: sudo nimbo-tor on")
        return 2

    preparar_perfil(args.perfil, PLANTILLA)
    proceso = lanzar(args.perfil)
    if not isinstance(proceso, subprocess.Popen):
        return 0
    anterior = estado
    if debe_avisar(None, estado):
        avisar(estado)
    while proceso.poll() is None:
        time.sleep(2)
        actual = leer_estado(ruta_estado)
        if debe_avisar(anterior, actual):
            avisar(actual)
        if actual:
            anterior = actual
    return 0


if __name__ == "__main__":
    sys.exit(main())
