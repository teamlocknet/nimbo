"""nimbo-navegar-tor — abre firefox-esr con el perfil Tor y avisa si hay fugas.

Se ejecuta como el usuario (sin sudo). Exige que el modo Tor esté activo
(`nimbo-tor on`). Mientras el navegador está abierto, lee el estado que deja el
vigilante y muestra una notificación si algo va mal (HU-08 CA-3). Falla hacia el aviso:
"sin estado", "estado viejo" o "vigilante en error" también avisan; nunca se toman
por "limpio".
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
MAX_EDAD_S = 10.0  # el vigilante escribe cada 2 s; más de 10 s sin cambios = algo va mal


def leer_estado(ruta: Path) -> dict | None:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def motivo_aviso(estado: dict | None, ahora: float) -> str | None:
    """Texto del aviso, o None si todo está bien."""
    if not estado:
        return "el vigilante de fugas no está funcionando (no hay estado)"
    if estado.get("vigilante") == "error":
        return f"el vigilante de fugas tiene un error: {estado.get('error', 'desconocido')}"
    try:
        actualizado = float(estado.get("actualizado", 0))
    except (TypeError, ValueError):
        return "el estado del vigilante de fugas es inválido (no se puede saber si hay fugas)"
    if ahora - actualizado > MAX_EDAD_S:
        return "el vigilante de fugas no se actualiza (puede haberse detenido)"
    if not estado.get("modo_tor"):
        return "el modo Tor se ha apagado"
    paquetes = estado.get("paquetes_descartados", 0)
    conexiones = len(estado.get("conexiones", []))
    if paquetes or conexiones:
        return (f"posible FUGA: {paquetes} paquetes bloqueados fuera de Tor y "
                f"{conexiones} conexiones directas. Detalle: sudo nimbo-leakcheck")
    return None


def preparar_perfil(perfil: Path, plantilla: Path) -> None:
    perfil.mkdir(parents=True, exist_ok=True)
    os.chmod(perfil, 0o700)
    shutil.copyfile(plantilla, perfil / "user.js")


def avisar(texto: str) -> None:
    subprocess.run(["notify-send", "--urgency=critical", "nimbo: modo Tor", texto], check=False)
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
        print("nimbo-navegar-tor: el modo Tor no está activo. Primero: "
              "sudo nimbo-red on && nimbo-tor on")
        return 2

    preparar_perfil(args.perfil, PLANTILLA)
    proceso = lanzar(args.perfil)
    if not isinstance(proceso, subprocess.Popen):
        return 0
    ultimo = None
    while True:
        motivo = motivo_aviso(leer_estado(ruta_estado), time.time())
        if motivo and motivo != ultimo:
            avisar(motivo)
        ultimo = motivo
        if proceso.poll() is not None:
            return 0
        time.sleep(2)


if __name__ == "__main__":
    sys.exit(main())
