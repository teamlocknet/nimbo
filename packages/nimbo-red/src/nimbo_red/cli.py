"""nimbo-red — red por cable solo a demanda (ADR-019).

  sudo nimbo-red on [interfaz]   levanta la interfaz por cable y pide UNA concesión DHCP
  sudo nimbo-red off             suelta la concesión y baja la interfaz
  nimbo-red estado               dice si hay red y en qué interfaz

nimbo arranca sin red: ninguna interfaz está configurada (hermetismo, RNF-01). Esto no
escribe en /etc/network/interfaces ni deja servicios: la concesión y el PID viven en /run,
así que al reiniciar el equipo vuelve a quedar sin red. Solo cable; Wi-Fi fuera de v1.

Códigos de salida: 0 OK · 1 error (sin interfaz, sin concesión…) · 2 sin privilegios.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

SYS_NET = Path("/sys/class/net")
RUN_DIR = Path("/run/nimbo-red")
ESPERA_DHCP = 30   # segundos máximos para conseguir la concesión
CABLE = re.compile(r"^(en|eth)[a-z0-9]{0,13}$")   # nombres del kernel/udev para Ethernet

Ejecutor = Callable[[list[str]], str]


def ejecutar_sistema(argv: list[str]) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def _root() -> bool:
    import os
    return os.geteuid() == 0


def es_wifi(sys_net: Path, nombre: str) -> bool:
    d = sys_net / nombre
    return (d / "wireless").exists() or (d / "phy80211").exists()


def interfaces_cable(sys_net: Path) -> list[str]:
    if not sys_net.is_dir():
        return []
    return sorted(p.name for p in sys_net.iterdir()
                  if CABLE.match(p.name) and not es_wifi(sys_net, p.name))


def elegir(pedida: str | None, sys_net: Path) -> str | None:
    """La interfaz a usar, o None (tras explicar por qué) si no hay una clara."""
    if pedida is not None:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,15}", pedida) or not (sys_net / pedida).exists():
            print(f"nimbo-red: no existe la interfaz {pedida!r}.")
            return None
        if es_wifi(sys_net, pedida):
            print(f"nimbo-red: {pedida} es Wi-Fi. En esta versión solo hay red por cable.")
            return None
        if not CABLE.match(pedida):
            print(f"nimbo-red: {pedida} no es una interfaz por cable.")
            return None
        return pedida
    cable = interfaces_cable(sys_net)
    if not cable:
        print("nimbo-red: no hay ninguna interfaz por cable. En esta versión solo hay red por cable.")
        return None
    if len(cable) > 1:
        print(f"nimbo-red: hay varias interfaces por cable ({', '.join(cable)}). "
              "Indica cuál: sudo nimbo-red on <interfaz>")
        return None
    return cable[0]


def con_direccion(ip_br: str, sys_net: Path) -> list[str]:
    """Interfaces por cable con una dirección global en la salida de `ip -br addr`.

    Es el estado real del kernel: en el live, live-boot levanta la red sin nimbo-red.
    No cuentan las de enlace local (fe80::/10, 169.254/16): no dan salida a ninguna red.
    """
    activas = []
    for linea in ip_br.splitlines():
        campos = linea.split()
        if len(campos) < 3:
            continue
        nombre = campos[0].split("@", 1)[0]
        if not CABLE.match(nombre) or es_wifi(sys_net, nombre):
            continue
        if any(not d.startswith(("fe80:", "169.254.")) for d in campos[2:]):
            activas.append(nombre)
    return sorted(activas)


def de_ifupdown(iface: str, ejecutar: Ejecutor) -> bool:
    """¿La interfaz la tiene levantada ifupdown (ifup@<iface>, como en el live)?"""
    try:
        return f"{iface}=" in ejecutar(["ifquery", "--state", iface])
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False   # no la gestiona, o ifupdown no está instalado


def _ficheros(run_dir: Path, iface: str) -> list[str]:
    return ["-pf", str(run_dir / f"dhclient.{iface}.pid"),
            "-lf", str(run_dir / f"dhclient.{iface}.leases")]


def encender(iface: str, ejecutar: Ejecutor, run_dir: Path) -> int:
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        ejecutar(["ip", "link", "set", "dev", iface, "up"])
        ejecutar(["timeout", str(ESPERA_DHCP), "dhclient", "-1", *_ficheros(run_dir, iface), iface])
    except subprocess.CalledProcessError:
        try:
            ejecutar(["ip", "link", "set", "dev", iface, "down"])
        except subprocess.CalledProcessError:
            pass
        print(f"nimbo-red: no se consiguió dirección por DHCP en {iface} "
              f"(espera máxima {ESPERA_DHCP} s). El equipo sigue sin red.")
        return 1
    (run_dir / "interfaz").write_text(iface + "\n", encoding="utf-8")
    print(f"nimbo-red: red activa en {iface}. Para apagarla: sudo nimbo-red off")
    return 0


def apagar(iface: str, ejecutar: Ejecutor, run_dir: Path) -> int:
    try:
        ejecutar(["dhclient", "-r", *_ficheros(run_dir, iface), iface])
    except subprocess.CalledProcessError:
        pass   # sin concesión que soltar: se baja igual
    rc = 0
    if de_ifupdown(iface, ejecutar):
        try:
            ejecutar(["ifdown", iface])   # suelta la concesión de su dhclient y lo para
        except subprocess.CalledProcessError:
            rc = 1
    for argv in (["ip", "addr", "flush", "dev", iface], ["ip", "link", "set", "dev", iface, "down"]):
        try:
            ejecutar(argv)
        except subprocess.CalledProcessError:
            rc = 1
    (run_dir / "interfaz").unlink(missing_ok=True)
    print(f"nimbo-red: {iface} apagada. El equipo queda sin red." if rc == 0 else
          f"nimbo-red: no se pudo bajar {iface} del todo. Revisa: ip -br addr")
    return rc


def activa(run_dir: Path) -> str | None:
    f = run_dir / "interfaz"
    return f.read_text(encoding="utf-8").strip() if f.is_file() else None


def main(argv: list[str] | None = None, ejecutar: Ejecutor = ejecutar_sistema,
         es_root: Callable[[], bool] = _root, sys_net: Path = SYS_NET,
         run_dir: Path = RUN_DIR) -> int:
    p = argparse.ArgumentParser(prog="nimbo-red", description=__doc__.splitlines()[0])
    p.add_argument("accion", choices=["on", "off", "estado"])
    p.add_argument("interfaz", nargs="?", help="interfaz por cable (obligatoria si hay varias)")
    args = p.parse_args(sys.argv[1:] if argv is None else argv)

    if args.accion == "estado":
        try:
            ip_br = ejecutar(["ip", "-br", "addr"])
        except subprocess.CalledProcessError:
            ip_br = ""
        print(ip_br, end="")
        iface = activa(run_dir)
        fuera = [i for i in con_direccion(ip_br, sys_net) if i != iface]
        if iface:
            print(f"nimbo-red: red activa en {iface}")
        for i in fuera:
            print(f"nimbo-red: red activa en {i}, levantada fuera de nimbo-red "
                  f"(en el live, por live-boot). Para apagarla: sudo nimbo-red off {i}")
        if not iface and not fuera:
            print("nimbo-red: sin red (apagada)")
        return 0

    if not es_root():
        print(f"nimbo-red: necesita privilegios. Usa: sudo nimbo-red {args.accion}")
        return 2

    if args.accion == "off":
        iface = args.interfaz or activa(run_dir) or elegir(None, sys_net)
        return apagar(iface, ejecutar, run_dir) if iface else 1

    iface = elegir(args.interfaz, sys_net)
    return encender(iface, ejecutar, run_dir) if iface else 1


if __name__ == "__main__":
    sys.exit(main())
