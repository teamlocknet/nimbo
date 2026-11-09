"""nimbo-tor on/off/estado: orden de los pasos y fallo cerrado (ADR-012, C1 + D2)."""
import subprocess

from nimbo_nav import tor_modo


class Registro:
    def __init__(self, falla_en=None):
        self.llamadas = []
        self.falla_en = falla_en

    def __call__(self, argv):
        self.llamadas.append(list(argv))
        if self.falla_en and argv[: len(self.falla_en)] == self.falla_en:
            raise subprocess.CalledProcessError(1, argv, "", "fallo simulado")
        return ""


def test_on_carga_la_tabla_antes_de_arrancar_tor():
    r = Registro()
    assert tor_modo.main(["on"], ejecutar=r, es_root=lambda: True) == 0
    assert r.llamadas == [
        ["nft", "-f", tor_modo.TABLA_NFT],
        ["systemctl", "start", "tor@default.service"],
        ["systemctl", "start", "nimbo-leakcheck.service"],
    ]


def test_on_falla_cerrado_si_la_tabla_no_carga():
    r = Registro(falla_en=["nft", "-f"])
    assert tor_modo.main(["on"], ejecutar=r, es_root=lambda: True) == 1
    assert ["systemctl", "start", "tor@default.service"] not in r.llamadas


def test_off_para_tor_y_borra_la_tabla():
    r = Registro()
    assert tor_modo.main(["off"], ejecutar=r, es_root=lambda: True) == 0
    assert r.llamadas == [
        ["systemctl", "stop", "nimbo-leakcheck.service"],
        ["systemctl", "stop", "tor@default.service"],
        ["nft", "delete", "table", "inet", "nimbo_tor"],
    ]


def test_off_tolera_tabla_ya_borrada():
    r = Registro(falla_en=["nft", "delete"])
    assert tor_modo.main(["off"], ejecutar=r, es_root=lambda: True) == 0


def test_exige_root(capsys):
    assert tor_modo.main(["on"], ejecutar=Registro(), es_root=lambda: False) == 2
    assert "sudo nimbo-tor" in capsys.readouterr().out


def test_estado(capsys):
    r = Registro()
    assert tor_modo.main(["estado"], ejecutar=r, es_root=lambda: True) == 0
    assert ["nft", "list", "table", "inet", "nimbo_tor"] in r.llamadas
    assert "activo" in capsys.readouterr().out
