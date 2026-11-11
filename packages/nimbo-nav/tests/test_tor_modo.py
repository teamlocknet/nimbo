"""nimbo-tor on/off/estado (ADR-012 aceptado, #45).

El encendido lo hace la unidad nimbo-modo-tor.service (tabla -> tor -> vigilante; al
parar, al revés). nimbo-tor solo arranca, para o consulta esa unidad: no corre como root
(systemd pide la autorización con polkit).
"""
import subprocess

from nimbo_nav import tor_modo


class Registro:
    def __init__(self, falla_en=None, salida=""):
        self.llamadas = []
        self.falla_en = falla_en
        self.salida = salida

    def __call__(self, argv):
        self.llamadas.append(list(argv))
        if self.falla_en and argv[: len(self.falla_en)] == self.falla_en:
            raise subprocess.CalledProcessError(1, argv, "", "fallo simulado")
        return self.salida


def test_on_arranca_la_unidad():
    r = Registro()
    assert tor_modo.main(["on"], ejecutar=r) == 0
    assert r.llamadas == [["systemctl", "start", "nimbo-modo-tor.service"]]


def test_off_para_la_unidad():
    r = Registro()
    assert tor_modo.main(["off"], ejecutar=r) == 0
    assert r.llamadas == [["systemctl", "stop", "nimbo-modo-tor.service"]]


def test_on_que_falla_avisa_sin_traceback(capsys):
    r = Registro(falla_en=["systemctl", "start"])
    assert tor_modo.main(["on"], ejecutar=r) == 1
    salida = capsys.readouterr().out
    assert "journalctl -u nimbo-modo-tor" in salida
    assert "Traceback" not in salida


def test_off_que_falla_avisa_sin_traceback_y_dice_que_la_red_sigue_cerrada(capsys):
    r = Registro(falla_en=["systemctl", "stop"])
    assert tor_modo.main(["off"], ejecutar=r) == 1
    salida = capsys.readouterr().out
    assert "red sigue cerrada" in salida
    assert "nft delete table inet nimbo_tor" in salida


def test_estado_activo(capsys):
    assert tor_modo.main(["estado"], ejecutar=Registro(salida="active\n")) == 0
    assert "activo" in capsys.readouterr().out


def test_estado_inactivo(capsys):
    r = Registro(falla_en=["systemctl", "is-active"])
    assert tor_modo.main(["estado"], ejecutar=r) == 0
    assert "inactivo" in capsys.readouterr().out
