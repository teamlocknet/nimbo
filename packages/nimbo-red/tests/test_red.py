"""nimbo-red on/off/estado: red por cable solo a demanda (ADR-019)."""
import subprocess

import pytest

from nimbo_red import cli


class Registro:
    """Ejecutor falso: guarda cada orden y puede fallar en una concreta."""

    def __init__(self, falla_en=None):
        self.llamadas = []
        self.falla_en = falla_en

    def __call__(self, argv):
        self.llamadas.append(list(argv))
        if self.falla_en and argv[: len(self.falla_en)] == self.falla_en:
            raise subprocess.CalledProcessError(1, argv, "", "fallo simulado")
        return ""


def sysfs(tmp_path, *ifaces):
    """Crea un /sys/class/net falso. 'wlan0:wifi' marca una interfaz Wi-Fi."""
    raiz = tmp_path / "net"
    raiz.mkdir()
    for nombre in ifaces:
        nombre, _, tipo = nombre.partition(":")
        d = raiz / nombre
        d.mkdir()
        if tipo == "wifi":
            (d / "wireless").mkdir()
    return raiz


def correr(tmp_path, args, ifaces=("lo", "enp0s3"), ejecutar=None, root=True):
    ejecutar = ejecutar or Registro()
    rc = cli.main(args, ejecutar=ejecutar, es_root=lambda: root,
                  sys_net=sysfs(tmp_path, *ifaces), run_dir=tmp_path / "run")
    return rc, ejecutar


# --- elegir la interfaz -------------------------------------------------------------

def test_lista_solo_interfaces_por_cable(tmp_path):
    raiz = sysfs(tmp_path, "lo", "enp0s3", "eth1", "wlp2s0:wifi", "wg0", "docker0")
    assert cli.interfaces_cable(raiz) == ["enp0s3", "eth1"]


def test_sin_interfaz_por_cable_falla(tmp_path, capsys):
    rc, r = correr(tmp_path, ["on"], ifaces=("lo", "wlp2s0:wifi"))
    assert rc == 1 and r.llamadas == []
    assert "no hay ninguna interfaz por cable" in capsys.readouterr().out


def test_varias_interfaces_exige_elegir(tmp_path, capsys):
    rc, r = correr(tmp_path, ["on"], ifaces=("enp0s3", "enp0s4"))
    assert rc == 1 and r.llamadas == []
    salida = capsys.readouterr().out
    assert "enp0s3" in salida and "enp0s4" in salida and "nimbo-red on <interfaz>" in salida


def test_varias_interfaces_con_una_elegida(tmp_path):
    rc, r = correr(tmp_path, ["on", "enp0s4"], ifaces=("enp0s3", "enp0s4"))
    assert rc == 0 and r.llamadas[0] == ["ip", "link", "set", "dev", "enp0s4", "up"]


def test_se_niega_con_wifi(tmp_path, capsys):
    rc, r = correr(tmp_path, ["on", "wlp2s0"], ifaces=("enp0s3", "wlp2s0:wifi"))
    assert rc == 1 and r.llamadas == []
    assert "Wi-Fi" in capsys.readouterr().out


def test_se_niega_con_interfaz_inexistente(tmp_path):
    rc, r = correr(tmp_path, ["on", "enp9s9"])
    assert rc == 1 and r.llamadas == []


def test_nombre_de_interfaz_raro_se_rechaza(tmp_path):
    rc, r = correr(tmp_path, ["on", "../etc"])
    assert rc == 1 and r.llamadas == []


# --- on / off -----------------------------------------------------------------------

def test_on_levanta_y_pide_una_concesion_en_run(tmp_path):
    rc, r = correr(tmp_path, ["on"])
    run = str(tmp_path / "run")
    assert rc == 0
    assert r.llamadas == [
        ["ip", "link", "set", "dev", "enp0s3", "up"],
        ["timeout", str(cli.ESPERA_DHCP), "dhclient", "-1",
         "-pf", f"{run}/dhclient.enp0s3.pid", "-lf", f"{run}/dhclient.enp0s3.leases", "enp0s3"],
    ]
    assert (tmp_path / "run" / "interfaz").read_text().strip() == "enp0s3"


def test_on_sin_concesion_baja_la_interfaz(tmp_path, capsys):
    rc, r = correr(tmp_path, ["on"], ejecutar=Registro(falla_en=["timeout"]))
    assert rc == 1
    assert r.llamadas[-1] == ["ip", "link", "set", "dev", "enp0s3", "down"]
    assert not (tmp_path / "run" / "interfaz").exists()
    assert "sin red" in capsys.readouterr().out


def test_off_suelta_la_concesion_y_baja_la_interfaz(tmp_path):
    correr(tmp_path, ["on"])
    rc, r = correr(tmp_path, ["off"])
    run = str(tmp_path / "run")
    assert rc == 0
    assert r.llamadas == [
        ["dhclient", "-r", "-pf", f"{run}/dhclient.enp0s3.pid",
         "-lf", f"{run}/dhclient.enp0s3.leases", "enp0s3"],
        ["ip", "addr", "flush", "dev", "enp0s3"],
        ["ip", "link", "set", "dev", "enp0s3", "down"],
    ]
    assert not (tmp_path / "run" / "interfaz").exists()


def test_off_recuerda_la_interfaz_aunque_haya_varias(tmp_path):
    correr(tmp_path, ["on", "enp0s4"], ifaces=("enp0s3", "enp0s4"))
    rc, r = correr(tmp_path, ["off"], ifaces=("enp0s3", "enp0s4"))
    assert rc == 0 and r.llamadas[-1] == ["ip", "link", "set", "dev", "enp0s4", "down"]


def test_off_baja_la_interfaz_aunque_falle_el_release(tmp_path):
    correr(tmp_path, ["on"])
    rc, r = correr(tmp_path, ["off"], ejecutar=Registro(falla_en=["dhclient", "-r"]))
    assert rc == 0 and r.llamadas[-1] == ["ip", "link", "set", "dev", "enp0s3", "down"]


# --- permisos y estado --------------------------------------------------------------

@pytest.mark.parametrize("accion", ["on", "off"])
def test_sin_root_sale_con_2_y_no_toca_nada(tmp_path, accion):
    rc, r = correr(tmp_path, [accion], root=False)
    assert rc == 2 and r.llamadas == []


def test_estado_sin_root_y_sin_red(tmp_path, capsys):
    rc, r = correr(tmp_path, ["estado"], root=False)
    assert rc == 0 and r.llamadas == [["ip", "-br", "addr"]]
    assert "sin red" in capsys.readouterr().out


def test_estado_con_red_activa(tmp_path, capsys):
    correr(tmp_path, ["on"])
    capsys.readouterr()
    rc, _ = correr(tmp_path, ["estado"], root=False)
    assert rc == 0 and "activa en enp0s3" in capsys.readouterr().out
