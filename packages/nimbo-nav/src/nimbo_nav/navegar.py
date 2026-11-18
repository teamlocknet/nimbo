"""nimbo-navegar-tor — abre firefox-esr con el perfil Tor y avisa si hay fugas.

Se ejecuta como el usuario (sin sudo). Exige que el modo Tor esté activo
(`sudo nimbo-tor on`). Mientras el navegador está abierto, lee el estado que deja el
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


def diagnostico(estado: dict | None, ahora: float) -> tuple[str, str] | None:
    """(clase, texto) del problema, o None si todo está bien. La CLASE dice qué va mal; el
    texto lleva además los detalles (p. ej. cuántos paquetes), que cambian con el tiempo."""
    if not estado:
        return "sin-estado", "el vigilante de fugas no está funcionando (no hay estado)"
    if estado.get("vigilante") == "error":
        return ("error", "el vigilante de fugas tiene un error: "
                         f"{estado.get('error', 'desconocido')}")
    try:
        actualizado = float(estado.get("actualizado", 0))
    except (TypeError, ValueError):
        return ("invalido", "el estado del vigilante de fugas es inválido "
                            "(no se puede saber si hay fugas)")
    if ahora - actualizado > MAX_EDAD_S:
        return "viejo", "el vigilante de fugas no se actualiza (puede haberse detenido)"
    if not estado.get("modo_tor"):
        return "apagado", "el modo Tor se ha apagado"
    paquetes = estado.get("paquetes_descartados", 0)
    conexiones = len(estado.get("conexiones", []))
    if paquetes or conexiones:
        return ("fuga", f"posible FUGA: {paquetes} paquetes bloqueados fuera de Tor y "
                        f"{conexiones} conexiones directas. Detalle: sudo nimbo-leakcheck")
    return None


def motivo_aviso(estado: dict | None, ahora: float) -> str | None:
    """Texto del aviso, o None si todo está bien."""
    d = diagnostico(estado, ahora)
    return d[1] if d else None


def preparar_perfil(perfil: Path, plantilla: Path) -> None:
    perfil.mkdir(parents=True, exist_ok=True)
    os.chmod(perfil, 0o700)
    shutil.copyfile(plantilla, perfil / "user.js")


def avisar(texto: str) -> None:
    # El aviso en pantalla lo muestra xfce4-notifyd (dependencia del paquete). Si no hay quien
    # lo muestre, el vigilante del navegador NO se cae: sigue vigilando y avisa por stderr.
    print(f"nimbo-navegar-tor: AVISO — {texto}", file=sys.stderr)
    try:
        subprocess.run(["notify-send", "--urgency=critical", "nimbo: modo Tor", texto],
                       check=False, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass


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
              "sudo nimbo-red on && sudo nimbo-tor on")
        return 2

    preparar_perfil(args.perfil, PLANTILLA)
    proceso = lanzar(args.perfil)
    if not isinstance(proceso, subprocess.Popen):
        return 0
    return vigilar(ruta_estado, proceso)


def vigilar(ruta_estado: Path, proceso, aviso: Callable[[str], None] = None,
            reloj: Callable[[], float] = time.time,
            dormir: Callable[[float], None] = time.sleep) -> int:
    """Mientras el navegador está abierto, avisa UNA vez cada vez que empieza un problema.

    Se compara la clase del problema, no el texto: una fuga que sigue sumando paquetes es la
    misma fuga y no repite la notificación (ensayo de la demo, 18-nov). Un problema distinto,
    o el mismo después de volver a estar limpio, sí avisa."""
    aviso = aviso or avisar
    ultima_clase = None
    while True:
        d = diagnostico(leer_estado(ruta_estado), reloj())
        clase = d[0] if d else None
        if d and clase != ultima_clase:
            aviso(d[1])
        ultima_clase = clase
        if proceso.poll() is not None:
            return 0
        dormir(2)


if __name__ == "__main__":
    sys.exit(main())
