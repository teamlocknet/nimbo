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
                    raise subprocess.CalledProcessError(r[1], argv, r[2],
                                                        r[3] if len(r) > 3 else "fallo simulado")
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


# --- Aviso "sin red" al encender (propuesta de Juan José, 16-nov) -----------------------
# /proc/net/route (IPv4): Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT
CABECERA_V4 = "Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n"
RUTA_LOCAL_V4 = "enp0s3\t0002000A\t00000000\t0001\t0\t0\t100\t00FFFFFF\t0\t0\t0\n"
DEFECTO_V4 = "enp0s3\t00000000\t0202000A\t0003\t0\t0\t100\t00000000\t0\t0\t0\n"
# /proc/net/ipv6_route: dest plen src plen nexthop metric refcnt use flags iface
CERO = "0" * 32
DEFECTO_V6_LO_RECHAZO = f"{CERO} 00 {CERO} 00 {CERO} ffffffff 00000001 00000000 00200200       lo\n"
DEFECTO_V6 = f"{CERO} 00 {CERO} 00 fe800000000000000000000000000001 00000400 00000001 00000000 00450003   enp0s3\n"


def _proc(tmp_path, v4=None, v6=None):
    proc = tmp_path / "proc_net"
    proc.mkdir()
    if v4 is not None:
        (proc / "route").write_text(CABECERA_V4 + v4, encoding="utf-8")
    if v6 is not None:
        (proc / "ipv6_route").write_text(v6, encoding="utf-8")
    return proc


def _on(tmp_path, proc):
    return tor_modo.main(["on"], ejecutar=Sistema(), sys_net=tmp_path / "sys_net", proc_net=proc)


def test_on_sin_ruta_por_defecto_avisa_y_sigue_activo(tmp_path, capsys):
    proc = _proc(tmp_path, v4=RUTA_LOCAL_V4, v6=DEFECTO_V6_LO_RECHAZO)
    assert _on(tmp_path, proc) == 0  # el modo SÍ está activo y bloquea
    salida = capsys.readouterr().out
    assert "modo Tor ACTIVO" in salida
    assert "Sin red: Tor no podrá conectarse hasta que haya red (nimbo-red on)." in salida


def test_on_con_ruta_por_defecto_ipv4_no_avisa(tmp_path, capsys):
    assert _on(tmp_path, _proc(tmp_path, v4=DEFECTO_V4, v6="")) == 0
    assert "Sin red" not in capsys.readouterr().out


def test_on_con_ruta_por_defecto_solo_ipv6_no_avisa(tmp_path, capsys):
    assert _on(tmp_path, _proc(tmp_path, v4="", v6=DEFECTO_V6_LO_RECHAZO + DEFECTO_V6)) == 0
    assert "Sin red" not in capsys.readouterr().out


def test_on_ruta_por_defecto_caida_cuenta_como_sin_red(tmp_path, capsys):
    caida = DEFECTO_V4.replace("\t0003\t", "\t0002\t")  # sin RTF_UP
    assert _on(tmp_path, _proc(tmp_path, v4=caida, v6="")) == 0
    assert "Sin red" in capsys.readouterr().out


def test_on_si_no_se_pueden_leer_las_rutas_no_inventa_el_aviso(tmp_path, capsys):
    assert _on(tmp_path, _proc(tmp_path)) == 0
    assert "Sin red" not in capsys.readouterr().out


def test_on_que_falla_no_da_el_aviso_sin_red(tmp_path, capsys):
    proc = _proc(tmp_path, v4=RUTA_LOCAL_V4, v6="")
    s = Sistema({("systemctl", "start"): ("falla", 1, "")})
    assert tor_modo.main(["on"], ejecutar=s, sys_net=tmp_path, proc_net=proc) == 1
    assert "Sin red" not in capsys.readouterr().out


# --- Sin polkit (ISO, 16-nov): systemd rechaza al usuario sin sudo -------------------------
SIN_PERMISO = "Failed to start nimbo-modo-tor.service: Access denied\n"


def test_on_sin_sudo_rechazado_por_systemd_dice_usa_sudo(tmp_path, capsys):
    s = Sistema({("systemctl", "start"): ("falla", 1, "", SIN_PERMISO)})
    assert tor_modo.main(["on"], ejecutar=s, sys_net=tmp_path) == 2
    salida = capsys.readouterr().out
    assert "sudo nimbo-tor on" in salida
    assert "systemd deshace" not in salida  # no llegó a arrancar nada


def test_off_sin_sudo_rechazado_por_systemd_dice_usa_sudo(tmp_path, capsys):
    s = Sistema({("systemctl", "stop"): ("falla", 1, "",
                                         "Failed to stop nimbo-modo-tor.service: "
                                         "Interactive authentication required.\n")})
    assert tor_modo.main(["off"], ejecutar=s, sys_net=tmp_path) == 2
    salida = capsys.readouterr().out
    assert "sudo nimbo-tor off" in salida
    assert "restaurada" not in salida
