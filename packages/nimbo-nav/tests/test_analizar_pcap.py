"""analizar_pcap.py (pruebas/): lectura de pcap y criterios de RF-NAV-01/02 en el host."""
import importlib.util
import ipaddress
import os
import struct
import sys
from pathlib import Path

# Al construir el .deb, pybuild ejecuta las pruebas desde una copia sin pruebas/:
# debian/rules exporta NIMBO_NAV_SRC con la raíz de la fuente (como en test_config.py).
_RAIZ = Path(os.environ.get("NIMBO_NAV_SRC") or Path(__file__).resolve().parents[1])
_RUTA = _RAIZ / "pruebas" / "analizar_pcap.py"
_spec = importlib.util.spec_from_file_location("analizar_pcap", _RUTA)
ap = importlib.util.module_from_spec(_spec)
sys.modules["analizar_pcap"] = ap  # dataclass lo necesita
_spec.loader.exec_module(ap)

MAC = b"\x02\x00\x00\x00\x00\x01" * 2


def _v4(src, dst, proto, carga):
    cab = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(carga), 0, 0, 64, proto, 0,
                      ipaddress.IPv4Address(src).packed, ipaddress.IPv4Address(dst).packed)
    return MAC + b"\x08\x00" + cab + carga


def _v6(src, dst, proto, carga):
    cab = struct.pack("!IHBB16s16s", 0x60000000, len(carga), proto, 64,
                      ipaddress.IPv6Address(src).packed, ipaddress.IPv6Address(dst).packed)
    return MAC + b"\x86\xdd" + cab + carga


def _tcp(sp, dp, banderas):
    return struct.pack("!HHIIBBHHH", sp, dp, 0, 0, 0x50, banderas, 1024, 0, 0)


def _udp(sp, dp, datos=b""):
    return struct.pack("!HHHH", sp, dp, 8 + len(datos), 0) + datos


def _consulta(nombre):
    q = b"".join(bytes([len(p)]) + p.encode() for p in nombre.split(".")) + b"\x00"
    return struct.pack("!HHHHHH", 1, 0x0100, 1, 0, 0, 0) + q + b"\x00\x01\x00\x01"


ARP = MAC + b"\x08\x06" + b"\x00" * 28


def _pcap(tmp_path, tramas, nombre="c.pcap"):
    datos = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    for n, t in enumerate(tramas):
        datos += struct.pack("<IIII", 1000 + n, 0, len(t), len(t)) + t
    f = tmp_path / nombre
    f.write_bytes(datos)
    return f


def test_reposo_limpio_pasa(tmp_path, capsys):
    f = _pcap(tmp_path, [ARP, _v4("0.0.0.0", "255.255.255.255", 17, _udp(68, 67)),
                         _v6("fe80::1", "ff02::2", 58, b"\x85\x00\x00\x00")])
    assert ap.main([str(f)]) == 0
    assert "Sospechosos: 0" in capsys.readouterr().out


def test_dns_y_syn_son_sospechosos(tmp_path, capsys):
    f = _pcap(tmp_path, [_v4("10.0.2.15", "10.0.2.3", 17, _udp(40000, 53, _consulta("firefox.settings.services.mozilla.com"))),
                         _v4("10.0.2.15", "1.2.3.4", 6, _tcp(40001, 8080, 0x02)),
                         _v4("10.0.2.15", "1.2.3.4", 6, _tcp(40001, 8080, 0x10))])
    assert ap.main([str(f)]) == 1
    salida = capsys.readouterr().out
    assert "Sospechosos: 2" in salida
    assert "firefox.settings.services.mozilla.com" in salida


def test_syn_ack_entrante_no_es_syn_sospechoso(tmp_path):
    p = ap.leer_pcap(_pcap(tmp_path, [_v4("1.2.3.4", "10.0.2.15", 6, _tcp(9001, 40001, 0x12))]))[0]
    assert not ap.es_sospechoso(p)


def test_tor_solo_con_reles_pasa(tmp_path, capsys):
    reles = tmp_path / "reles.txt"
    reles.write_text("1.2.3.4\n[2001:db8::9]\n", encoding="utf-8")
    f = _pcap(tmp_path, [ARP, _v4("10.0.2.15", "1.2.3.4", 6, _tcp(40001, 443, 0x02)),
                         _v6("2001:db8::1", "2001:db8::9", 6, _tcp(40002, 9001, 0x10))])
    assert ap.main([str(f), "--reles", str(reles)]) == 0
    assert "Fuera del túnel: 0" in capsys.readouterr().out


def test_tor_con_paquete_fuera_o_dns_falla(tmp_path):
    reles = tmp_path / "reles.txt"
    reles.write_text("1.2.3.4\n", encoding="utf-8")
    fuera = _pcap(tmp_path, [_v4("10.0.2.15", "5.6.7.8", 6, _tcp(40001, 443, 0x02))], "f.pcap")
    assert ap.main([str(fuera), "--reles", str(reles)]) == 1
    # DNS hacia un relé sigue siendo fallo: CA-1 pide 0 DNS
    dns = _pcap(tmp_path, [_v4("10.0.2.15", "1.2.3.4", 17, _udp(40000, 53))], "d.pcap")
    assert ap.main([str(dns), "--reles", str(reles)]) == 1


def test_fichero_que_no_es_pcap_da_2(tmp_path):
    f = tmp_path / "x.pcap"
    f.write_bytes(b"\x0a\x0d\x0d\x0a" + b"\x00" * 40)
    assert ap.main([str(f)]) == 2


def test_ipv6_con_cabecera_salto_a_salto_se_clasifica(tmp_path):
    # MLDv2 (ICMPv6 143) tras una cabecera salto a salto: puesta en marcha, no fuga
    hbh = bytes([58, 0, 5, 2, 0, 0, 1, 0])
    mld = _v6("fe80::1", "ff02::16", 0, hbh + b"\x8f\x00\x00\x00")
    p = ap.leer_pcap(_pcap(tmp_path, [mld]))[0]
    assert p.proto == "icmp6" and ap.es_puesta_en_marcha(p)


def test_ip_de_protocolo_desconocido_fuera_de_reles_cuenta(tmp_path):
    reles = tmp_path / "reles.txt"
    reles.write_text("1.2.3.4\n", encoding="utf-8")
    gre = _pcap(tmp_path, [_v4("10.0.2.15", "5.6.7.8", 47, b"\x00" * 8)], "g.pcap")
    assert ap.main([str(gre), "--reles", str(reles)]) == 1


def test_lista_de_reles_mal_formada_da_2_sin_traceback(tmp_path, capsys):
    reles = tmp_path / "reles.txt"
    reles.write_text("no-es-una-ip\n", encoding="utf-8")
    f = _pcap(tmp_path, [ARP])
    assert ap.main([str(f), "--reles", str(reles)]) == 2
    assert "Traceback" not in capsys.readouterr().out
