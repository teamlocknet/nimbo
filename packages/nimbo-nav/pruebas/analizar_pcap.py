#!/usr/bin/env python3
"""analizar_pcap.py — analiza en el HOST una captura de la tarjeta de la VM (RF-NAV-01/02).

Para medir sobre la ISO instalada sin meter nada en el sistema probado: la captura la hace
el hipervisor (VirtualBox `nictrace`, QEMU `filter-dump`) y este script la lee con Python
puro (sin tcpdump ni dependencias). Criterios, los mismos que comun.sh y
prueba-fugas-tor.sh:

  sospechoso  DNS (53), NTP (123), HTTP/HTTPS (80/443) o un SYN TCP (sin ACK).
              ARP, DHCP y NDP link-local son puesta en marcha de la NIC y no cuentan.
  fuera       (con --reles) paquete IP que no va ni viene de un relé de tor y no es
              puesta en marcha (ARP, DHCP 67/68, ICMPv6 a ff02::/16 o fe80::/10).

  python3 analizar_pcap.py reposo.pcap                       # RF-NAV-01
  python3 analizar_pcap.py tor.pcap --reles reles-ip.txt     # RF-NAV-02

Código de salida: 0 si no hay sospechosos (o, con --reles, 0 DNS y 0 fuera); 1 si los hay;
2 si el fichero no es un pcap legible.
"""
from __future__ import annotations

import argparse
import ipaddress
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

PUERTOS_SOSPECHOSOS = {53, 123, 80, 443}
DHCP = {67, 68, 546, 547}


@dataclass
class Paquete:
    t: float
    proto: str              # "arp", "tcp", "udp", "icmp", "icmp6", "otro"
    src: str = ""
    dst: str = ""
    sport: int = 0
    dport: int = 0
    syn_sin_ack: bool = False
    dns_nombre: str = ""

    def linea(self) -> str:
        if self.proto in ("tcp", "udp"):
            extra = " SYN" if self.syn_sin_ack else ""
            extra += f" {self.dns_nombre}?" if self.dns_nombre else ""
            return f"{self.t:.6f} {self.proto} {self.src}.{self.sport} > {self.dst}.{self.dport}{extra}"
        return f"{self.t:.6f} {self.proto} {self.src} > {self.dst}"


def _nombre_dns(datos: bytes) -> str:
    """Primer nombre de la sección de preguntas (solo consultas, sin compresión)."""
    if len(datos) < 13 or datos[2] & 0x80:      # QR=1: respuesta
        return ""
    i, partes = 12, []
    while i < len(datos) and datos[i] and len(partes) < 64:
        n = datos[i]
        if n & 0xC0:
            break
        partes.append(datos[i + 1:i + 1 + n].decode("ascii", "replace"))
        i += 1 + n
    return ".".join(partes)


def _transporte(p: Paquete, proto: int, datos: bytes) -> None:
    if proto == 6 and len(datos) >= 14:
        p.proto = "tcp"
        p.sport, p.dport = struct.unpack("!HH", datos[:4])
        banderas = datos[13]
        p.syn_sin_ack = bool(banderas & 0x02) and not banderas & 0x10
    elif proto == 17 and len(datos) >= 8:
        p.proto = "udp"
        p.sport, p.dport = struct.unpack("!HH", datos[:4])
        if 53 in (p.sport, p.dport):
            p.dns_nombre = _nombre_dns(datos[8:])
    elif proto == 1:
        p.proto = "icmp"
    elif proto == 58:
        p.proto = "icmp6"


def decodificar(t: float, trama: bytes) -> Paquete:
    p = Paquete(t, "otro")
    if len(trama) < 14:
        return p
    tipo, i = struct.unpack("!H", trama[12:14])[0], 14
    while tipo in (0x8100, 0x88A8) and len(trama) >= i + 4:   # VLAN
        tipo, i = struct.unpack("!H", trama[i + 2:i + 4])[0], i + 4
    ip = trama[i:]
    if tipo == 0x0806:
        p.proto = "arp"
    elif tipo == 0x0800 and len(ip) >= 20:
        ihl = (ip[0] & 0x0F) * 4
        p.src, p.dst = str(ipaddress.IPv4Address(ip[12:16])), str(ipaddress.IPv4Address(ip[16:20]))
        _transporte(p, ip[9], ip[ihl:])
    elif tipo == 0x86DD and len(ip) >= 40:
        p.src, p.dst = str(ipaddress.IPv6Address(ip[8:24])), str(ipaddress.IPv6Address(ip[24:40]))
        sig, resto = ip[6], ip[40:]
        # Cabeceras de extensión (salto a salto, enrutamiento, opciones de destino): MLD,
        # por ejemplo, va tras una salto a salto. Sin esto, ese tráfico quedaría sin clasificar.
        while sig in (0, 43, 60) and len(resto) >= 8:
            sig, resto = resto[0], resto[(resto[1] + 1) * 8:]
        _transporte(p, sig, resto)
    return p


def leer_pcap(ruta: Path) -> list[Paquete]:
    datos = Path(ruta).read_bytes()
    if len(datos) < 24:
        raise ValueError("no es un pcap: demasiado corto")
    magia = datos[:4]
    if magia in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"):
        e = "<"
    elif magia in (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d"):
        e = ">"
    else:
        raise ValueError("no es un pcap clásico (¿pcapng?)")
    nano = magia in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d")
    enlace = struct.unpack(e + "I", datos[20:24])[0]
    if enlace != 1:
        raise ValueError(f"tipo de enlace {enlace} no soportado (se espera Ethernet = 1)")
    paquetes, i = [], 24
    while i + 16 <= len(datos):
        seg, frac, incl, _orig = struct.unpack(e + "IIII", datos[i:i + 16])
        i += 16
        trama = datos[i:i + incl]
        i += incl
        paquetes.append(decodificar(seg + frac / (1e9 if nano else 1e6), trama))
    return paquetes


def es_puesta_en_marcha(p: Paquete) -> bool:
    if p.proto == "arp":
        return True
    if p.proto == "udp" and (p.sport in DHCP or p.dport in DHCP):
        return True
    if p.proto == "icmp6":
        dst = ipaddress.ip_address(p.dst)
        return dst in ipaddress.ip_network("ff02::/16") or dst in ipaddress.ip_network("fe80::/10")
    return False


def es_sospechoso(p: Paquete) -> bool:
    if p.proto not in ("tcp", "udp"):
        return False
    return (p.sport in PUERTOS_SOSPECHOSOS or p.dport in PUERTOS_SOSPECHOSOS
            or p.syn_sin_ack)


def es_dns(p: Paquete) -> bool:
    return p.proto in ("tcp", "udp") and 53 in (p.sport, p.dport)


def fuera_del_tunel(p: Paquete, reles: set[str]) -> bool:
    if es_puesta_en_marcha(p) or not p.src:   # sin IP (tramas que no son IP ni ARP): no salen
        return False
    return p.src not in reles and p.dst not in reles


def leer_reles(ruta: Path) -> set[str]:
    reles = set()
    for linea in Path(ruta).read_text(encoding="utf-8").split():
        linea = linea.strip().strip("[]")
        if linea:
            reles.add(str(ipaddress.ip_address(linea)))
    return reles


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pcap", type=Path)
    ap.add_argument("--reles", type=Path, help="IP de los relés de tor (una por línea): RF-NAV-02")
    a = ap.parse_args(argv)
    try:
        paquetes = leer_pcap(a.pcap)
    except (OSError, ValueError) as e:
        print(f"analizar_pcap: {a.pcap}: {e}")
        return 2

    dns = [p for p in paquetes if es_dns(p)]
    print(f"- Paquetes capturados: {len(paquetes)} · DNS: {len(dns)}")
    if a.reles:
        try:
            reles = leer_reles(a.reles)
        except (OSError, ValueError) as e:
            print(f"analizar_pcap: {a.reles}: {e}")
            return 2
        malos = [p for p in paquetes if fuera_del_tunel(p, reles)]
        print(f"- Relés de tor: {len(reles)} · **Fuera del túnel: {len(malos)}**")
        titulo, ok = "Fuera del túnel", not dns and not malos
    else:
        malos = [p for p in paquetes if es_sospechoso(p)]
        print(f"- **Sospechosos: {len(malos)}**")
        titulo, ok = "Sospechosos", not malos
    print(f"\n## {titulo} (primeros 50)\n```")
    for p in malos[:50]:
        print(p.linea())
    print("```")
    nombres: dict[str, int] = {}
    for p in dns:
        if p.dns_nombre:
            nombres[p.dns_nombre] = nombres.get(p.dns_nombre, 0) + 1
    if nombres:
        print("\n## Nombres consultados por DNS\n```")
        for n, c in sorted(nombres.items(), key=lambda x: -x[1]):
            print(f"{c:6d} {n}")
        print("```")
    print("\nVEREDICTO: " + ("PASA" if ok else "FALLA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
