"""Lógica pura de detección de fugas (RF-NAV-02, HU-08 CA-2/CA-3)."""
import json

import pytest

from nimbo_nav.fugas import Conexion, conexiones_fuera_de_tor, evaluar, leer_contador


def _contador(paquetes: int) -> str:
    return json.dumps({"nftables": [
        {"metainfo": {"version": "1.0.6", "json_schema_version": 1}},
        {"counter": {"family": "inet", "name": "fugas", "table": "nimbo_tor",
                     "handle": 2, "packets": paquetes, "bytes": paquetes * 60}},
    ]})


def test_leer_contador():
    assert leer_contador(_contador(0)) == 0
    assert leer_contador(_contador(7)) == 7


def test_leer_contador_sin_contador_es_error():
    with pytest.raises(ValueError):
        leer_contador(json.dumps({"nftables": [{"metainfo": {}}]}))


SS = """\
tcp   ESTAB     0      0         10.0.2.15:43210      185.220.101.4:9001  users:(("tor",pid=900,fd=10))
tcp   ESTAB     0      0         127.0.0.1:44000          127.0.0.1:9050  users:(("firefox-esr",pid=1300,fd=80))
tcp   ESTAB     0      0         127.0.0.1:9050           127.0.0.1:44000 users:(("tor",pid=900,fd=12))
tcp   SYN-SENT  0      1         10.0.2.15:5555      93.184.216.34:443   users:(("curl",pid=1200,fd=5))
udp   ESTAB     0      0         10.0.2.15:40000          10.0.2.3:53    users:(("firefox-esr",pid=1300,fd=90))
tcp   ESTAB     0      0             [::1]:5000              [::1]:6000  users:(("x",pid=1,fd=1))
tcp   SYN-SENT  0      1   [2001:db8::15]:6000  [2606:4700::1111]:443
"""


def test_conexiones_fuera_de_tor():
    fugas = conexiones_fuera_de_tor(SS)
    assert fugas == [
        Conexion("tcp", "SYN-SENT", "10.0.2.15:5555", "93.184.216.34:443", "curl"),
        Conexion("udp", "ESTAB", "10.0.2.15:40000", "10.0.2.3:53", "firefox-esr"),
        Conexion("tcp", "SYN-SENT", "[2001:db8::15]:6000", "[2606:4700::1111]:443", "desconocido"),
    ]


def test_conexiones_fuera_de_tor_vacio():
    assert conexiones_fuera_de_tor("") == []


def test_evaluar():
    limpio = evaluar(0, [])
    assert limpio.limpio and limpio.paquetes_descartados == 0
    sucio = evaluar(3, [])
    assert not sucio.limpio
    sucio2 = evaluar(0, [Conexion("tcp", "SYN-SENT", "a:1", "b:2", "curl")])
    assert not sucio2.limpio
