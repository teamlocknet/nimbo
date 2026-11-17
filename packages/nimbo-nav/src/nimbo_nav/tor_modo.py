"""nimbo-tor — enciende y apaga el modo Tor (ADR-012 aceptado, #45; revisión de #59).

  sudo nimbo-tor on   arranca nimbo-modo-tor.service: tabla nftables -> tor -> vigilante
  sudo nimbo-tor off  la para en orden inverso: vigilante -> tor -> tabla
  nimbo-tor estado    dice si el modo está activo, inactivo o en fallo

nimbo-tor solo pide a systemd que arranque o pare la unidad. Se usa con sudo, como
nimbo-red: la ISO no trae polkit, así que sin sudo systemd lo rechaza (medido el 16-nov)
y nimbo-tor lo dice. La red la levanta antes `nimbo-red on` (ADR-019).
Nunca dice "red restaurada" sin comprobar antes el estado real de la unidad (ADR-009).
En v1, el modo Tor y la red del equipo (nimbo-net) son mutuamente excluyentes.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Callable

UNIDAD = "nimbo-modo-tor.service"
# Interfaz de nimbo-net (WireGuard): la misma que INTERFAZ de nimbo_net/cli.py (ADR-011, #66).
# Debe coincidir con AssertPathExists= de nimbo-modo-tor.service.
INTERFAZ_NIMBO_NET = "wg-nimbo"

Ejecutor = Callable[[list[str]], str]


def ejecutar_sistema(argv: list[str]) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def _detalle(e: subprocess.CalledProcessError) -> str:
    return (e.stderr or "").strip() or f"código {e.returncode}"


def _sin_permiso(e: subprocess.CalledProcessError) -> bool:
    """systemd rechazó la orden por falta de permisos. La ISO no trae polkit (medido el
    16-nov): sin sudo, systemctl start/stop responde "Access denied" o pide una
    autenticación interactiva que nadie puede dar."""
    texto = (e.stderr or "").lower()
    return "access denied" in texto or "interactive authentication required" in texto


def estado_unidad(ejecutar: Ejecutor) -> str:
    """'active', 'inactive', 'failed', ... (systemctl is-active sale con ≠ 0 si no está activa)."""
    try:
        return ejecutar(["systemctl", "is-active", UNIDAD]).strip()
    except subprocess.CalledProcessError as e:
        return (e.output or "").strip() or "desconocido"


def nimbo_net_activo(sys_net: Path) -> bool:
    return (Path(sys_net) / INTERFAZ_NIMBO_NET).exists()


# Banderas de las rutas del núcleo (include/uapi/linux/route.h).
_RTF_UP = 0x0001
_RTF_REJECT = 0x0200


def hay_ruta_por_defecto(proc_net: Path) -> bool | None:
    """True si alguna interfaz (no lo) tiene una ruta por defecto activa, IPv4 o IPv6.
    False si se leyeron las tablas y no hay ninguna. None si no se pudieron leer: en ese
    caso no se avisa, para no inventar un "sin red" que no se ha comprobado."""
    leidas = False
    try:
        lineas = (proc_net / "route").read_text(encoding="utf-8").splitlines()[1:]
        leidas = True
        for linea in lineas:
            c = linea.split()
            # Iface Destination Gateway Flags RefCnt Use Metric Mask ...
            if (len(c) >= 8 and c[0] != "lo" and c[1] == "00000000" and c[7] == "00000000"
                    and int(c[3], 16) & _RTF_UP):
                return True
    except (OSError, ValueError):
        pass
    try:
        lineas = (proc_net / "ipv6_route").read_text(encoding="utf-8").splitlines()
        leidas = True
        for linea in lineas:
            c = linea.split()
            # dest plen src plen nexthop metric refcnt use flags iface
            if len(c) >= 10 and c[9] != "lo" and c[1] == "00" and int(c[0], 16) == 0:
                banderas = int(c[8], 16)
                if banderas & _RTF_UP and not banderas & _RTF_REJECT:
                    return True
    except (OSError, ValueError):
        pass
    return False if leidas else None


def encender(ejecutar: Ejecutor, sys_net: Path, proc_net: Path = Path("/proc/net")) -> int:
    if nimbo_net_activo(sys_net):
        print("nimbo-tor: la red del equipo (nimbo-net) está activa. El modo Tor y nimbo-net no "
              "pueden estar activos a la vez en v1. Primero: nimbo-net leave")
        return 2
    try:
        ejecutar(["systemctl", "start", UNIDAD])
    except subprocess.CalledProcessError as e:
        if _sin_permiso(e):
            print("nimbo-tor: hace falta sudo para activar el modo Tor. No se activó nada; "
                  "la red sigue como estaba.\nUsa: sudo nimbo-tor on")
            return 2
        print(f"nimbo-tor: no se pudo activar el modo Tor ({_detalle(e)}).\n"
              "systemd deshace los pasos que llegaron a hacerse (ExecStopPost): tor parado y "
              "tabla borrada; la red sigue como estaba.\n"
              "Detalle: journalctl -u nimbo-modo-tor -b · Comprueba con: nimbo-tor estado")
        return 1
    print("nimbo-tor: modo Tor ACTIVO. Abre \"Navegar por Tor\" o ejecuta: nimbo-navegar-tor\n"
          "Mientras esté activo, solo tor puede salir a la red.")
    if hay_ruta_por_defecto(proc_net) is False:
        # El modo sí está activo y bloquea (código 0), pero sin ruta tor no llega a ningún
        # relé y el navegador se queda esperando sin explicación.
        print("Sin red: Tor no podrá conectarse hasta que haya red (nimbo-red on).")
    return 0


def apagar(ejecutar: Ejecutor, sys_net: Path) -> int:
    try:
        ejecutar(["systemctl", "stop", UNIDAD])
    except subprocess.CalledProcessError as e:
        if _sin_permiso(e):
            print("nimbo-tor: hace falta sudo para apagar el modo Tor. Sigue como estaba.\n"
                  "Usa: sudo nimbo-tor off")
            return 2
        print(f"nimbo-tor: no se pudo apagar el modo Tor del todo ({_detalle(e)}).\n"
              "La red sigue cerrada (lo seguro). Revisa: journalctl -u nimbo-modo-tor -b\n"
              "Para abrirla a mano, con sudo: systemctl stop tor@default.service && "
              "nft delete table inet nimbo_tor")
        return 1
    estado = estado_unidad(ejecutar)
    if estado == "failed":
        # systemctl stop devuelve 0 sobre una unidad fallida sin ejecutar ExecStop=.
        try:
            ejecutar(["systemctl", "reset-failed", UNIDAD])
        except subprocess.CalledProcessError:
            pass
        print("nimbo-tor: el modo Tor estaba en fallo (no llegó a arrancar bien). systemd ya "
              "ejecutó la limpieza (ExecStopPost), pero no se puede confirmar desde aquí.\n"
              "Comprueba la red; si sigue cerrada, con sudo: nft delete table inet nimbo_tor")
        return 1
    if estado != "inactive":
        print(f"nimbo-tor: la unidad quedó en estado '{estado}', no apagada. La red puede "
              "seguir cerrada. Revisa: journalctl -u nimbo-modo-tor -b")
        return 1
    print("nimbo-tor: modo Tor APAGADO. Red normal restaurada.")
    return 0


def estado(ejecutar: Ejecutor, sys_net: Path) -> int:
    e = estado_unidad(ejecutar)
    if e == "active":
        print("nimbo-tor: modo Tor activo")
        return 0
    if e == "failed":
        print("nimbo-tor: el modo Tor falló al arrancar. Detalle: journalctl -u nimbo-modo-tor -b"
              " · Para limpiar: sudo nimbo-tor off")
        return 1
    print("nimbo-tor: modo Tor inactivo")
    return 0


def main(argv: list[str] | None = None, ejecutar: Ejecutor = ejecutar_sistema,
         sys_net: Path = Path("/sys/class/net"), proc_net: Path = Path("/proc/net")) -> int:
    p = argparse.ArgumentParser(prog="nimbo-tor", description=__doc__.splitlines()[0])
    p.add_argument("accion", choices=["on", "off", "estado"])
    args = p.parse_args(sys.argv[1:] if argv is None else argv)
    if args.accion == "on":
        return encender(ejecutar, sys_net, proc_net)
    return {"off": apagar, "estado": estado}[args.accion](ejecutar, sys_net)


if __name__ == "__main__":
    sys.exit(main())
