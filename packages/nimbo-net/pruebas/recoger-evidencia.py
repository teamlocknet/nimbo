#!/usr/bin/env python3
"""Consulta una VM: no activa la VPN, no cambia red ni muestra claves."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


def consultar(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True,
                          timeout=10).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fase", choices=["reposo", "tunel", "limpio"])
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("ejecutar dentro de la VM con sudo")
    fallos = 0
    def resultado(ok, texto):
        nonlocal fallos
        print(("OK: " if ok else "PENDIENTE/FALLO: ") + texto)
        if not ok:
            fallos += 1
    try:
        print("FASE: " + args.fase)
        print("kernel: " + consultar(["uname", "-r"]).strip())
        print(consultar(["dpkg-query", "-W", "nimbo-net", "nimbo-red", "wireguard-tools"]).strip())
        enlaces = json.loads(consultar(["ip", "-details", "-j", "link", "show"]))
        wg = next((e for e in enlaces if e.get("ifname") == "wg-nimbo"), None)
        print("RUTAS IPv4: " + consultar(["ip", "-j", "route", "show"]).strip())
        dns = Path("/etc/resolv.conf")
        print("resolv.conf SHA256: " + (hashlib.sha256(dns.read_bytes()).hexdigest() if dns.exists() else "ausente"))
        tables = json.loads(consultar(["nft", "-j", "list", "tables"]))
        tor = any(e.get("table", {}).get("family") == "inet" and
                  e.get("table", {}).get("name") == "nimbo_tor" for e in tables["nftables"])
        resultado(not tor, "sin tabla inet nimbo_tor en la medicion VPN")
        if args.fase == "tunel":
            resultado(wg is not None and wg.get("linkinfo", {}).get("info_kind") == "wireguard",
                      "wg-nimbo es interfaz WireGuard")
            if wg:
                resultado("UP" in wg.get("flags", []), "wg-nimbo arriba")
                handshakes = consultar(["wg", "show", "wg-nimbo", "latest-handshakes"])
                # Imprimir solo cantidades: nunca wg dump, showconf o private-key.
                stamps = [int(line.split()[1]) for line in handshakes.splitlines()]
                resultado(len(stamps) == 1 and stamps[0] > 0, "un par con handshake registrado")
                transfer = consultar(["wg", "show", "wg-nimbo", "transfer"])
                values = [line.split()[1:] for line in transfer.splitlines()]
                print("transferencia RX/TX (bytes): " + repr([[int(a), int(b)] for a, b in values]))
                print("Handshake/counters historicos no prueban por si solos conectividad actual.")
            iface_path = Path("/run/nimbo-red/interfaz")
            iface = iface_path.read_text().strip() if iface_path.exists() else ""
            resultado(bool(re.fullmatch(r"(?:en|eth)[a-z0-9]{0,13}", iface)), "interfaz fisica registrada por nimbo-red")
            for scope in ["all", "default", "wg-nimbo"] + ([iface] if iface else []):
                if scope == "wg-nimbo" and wg is None:
                    continue
                value = consultar(["sysctl", "-n", "net.ipv4.conf." + scope + ".rp_filter"]).strip()
                resultado(value == "1", "rp_filter " + scope + "=" + value + " (exigido 1)")
        else:
            resultado(wg is None, "sin wg-nimbo")
        print("LISTENERS (instantanea; no es captura de trafico):")
        print(consultar(["ss", "-H", "-lntu"]).strip() or "ninguno")
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError):
        print("FALLO: no se pudo completar una consulta; no se imprimen datos privados ni stderr")
        return 1
    print("FALLOS: " + str(fallos))
    print("Esta consulta no acredita cifrado por captura, hermetismo 0/0 ni exclusion concurrente con Tor.")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
