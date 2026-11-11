"""nimbo-tor on/off/estado (ADR-012 aceptado, #45; revisión de #59).

El encendido lo hace la unidad nimbo-modo-tor.service (tabla -> tor -> vigilante; al
parar, al revés). nimbo-tor solo arranca, para o consulta esa unidad: no corre como root.
Nunca afirma "red restaurada" sin comprobar el estado real de la unidad.
"""
import subprocess

from nimbo_nav import tor_modo


class Sistema:
    """Simula systemctl. respuestas: prefijo de argv -> salida, o ('falla', código, salida)."""

    def __init__(self, respuestas=None):
        self.llamadas = []
        self.respuestas = respuestas or {}

    def __call__(self, argv):
        self.llamadas.append(list(argv))
        for prefijo, r in self.respuestas.items():
            if tuple(argv[: len(prefijo)]) == prefijo:
                if isinstance(r, tuple) and r[0] == "falla":
                    raise subprocess.CalledProcessError(r[1], argv, r[2], "fallo simulado")
                return r
        return ""


ACTIVO = ("systemctl", "is-active")


def test_on_arranca_la_unidad(tmp_path):
    s = Sistema()
    assert tor_modo.main(["on"], ejecutar=s, sys_net=tmp_path) == 0
    assert ["systemctl", "start", "nimbo-modo-tor.service"] in s.llamadas


def test_on_que_falla_avisa_sin_traceback(tmp_path, capsys):
    s = Sistema({("systemctl", "start"): ("falla", 1, "")})
    assert tor_modo.main(["on"], ejecutar=s, sys_net=tmp_path) == 1
    salida = capsys.readouterr().out
    assert "journalctl -u nimbo-modo-tor" in salida
    assert "Traceback" not in salida


def test_on_se_niega_si_nimbo_net_esta_activo(tmp_path, capsys):
    (tmp_path / tor_modo.INTERFAZ_NIMBO_NET).mkdir()
    s = Sistema()
    assert tor_modo.main(["on"], ejecutar=s, sys_net=tmp_path) == 2
    assert "nimbo-net leave" in capsys.readouterr().out
    assert not any(a[:2] == ["systemctl", "start"] for a in s.llamadas)


def test_off_limpio_dice_restaurada(tmp_path, capsys):
    s = Sistema({ACTIVO: ("falla", 3, "inactive\n")})
    assert tor_modo.main(["off"], ejecutar=s, sys_net=tmp_path) == 0
    assert s.llamadas[0] == ["systemctl", "stop", "nimbo-modo-tor.service"]
    assert "restaurada" in capsys.readouterr().out


def test_off_con_la_unidad_fallida_no_dice_restaurada(tmp_path, capsys):
    # systemctl stop devuelve 0 sobre una unidad fallida, pero no ejecuta ExecStop=.
    s = Sistema({ACTIVO: ("falla", 3, "failed\n")})
    assert tor_modo.main(["off"], ejecutar=s, sys_net=tmp_path) == 1
    salida = capsys.readouterr().out
    assert "restaurada" not in salida
    assert "fallo" in salida
    assert ["systemctl", "reset-failed", "nimbo-modo-tor.service"] in s.llamadas


def test_off_que_falla_avisa_sin_traceback_y_dice_que_la_red_sigue_cerrada(tmp_path, capsys):
    s = Sistema({("systemctl", "stop"): ("falla", 1, "")})
    assert tor_modo.main(["off"], ejecutar=s, sys_net=tmp_path) == 1
    salida = capsys.readouterr().out
    assert "red sigue cerrada" in salida
    assert "nft delete table inet nimbo_tor" in salida


def test_estado_activo(tmp_path, capsys):
    assert tor_modo.main(["estado"], ejecutar=Sistema({ACTIVO: "active\n"}), sys_net=tmp_path) == 0
    assert "modo Tor activo" in capsys.readouterr().out


def test_estado_inactivo(tmp_path, capsys):
    s = Sistema({ACTIVO: ("falla", 3, "inactive\n")})
    assert tor_modo.main(["estado"], ejecutar=s, sys_net=tmp_path) == 0
    assert "inactivo" in capsys.readouterr().out


def test_estado_fallido(tmp_path, capsys):
    s = Sistema({ACTIVO: ("falla", 3, "failed\n")})
    assert tor_modo.main(["estado"], ejecutar=s, sys_net=tmp_path) == 1
    assert "falló" in capsys.readouterr().out
