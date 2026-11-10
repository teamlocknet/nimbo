"""CLI nimbo-leakcheck: códigos de salida y fichero de estado (HU-08 CA-3)."""
import json
import subprocess

from nimbo_nav import leakcheck


def _contador(paquetes):
    return json.dumps({"nftables": [{"counter": {"name": "fugas", "packets": paquetes}}]})


class Ejecutor:
    """Simula `nft` y `ss` sin tocar el sistema."""

    def __init__(self, contador=None, ss=""):
        self.contador = contador
        self.ss = ss

    def __call__(self, argv):
        if argv[0] == "nft":
            if self.contador is None:
                raise subprocess.CalledProcessError(1, argv, "", "Error: No such file or directory")
            return _contador(self.contador)
        if argv[0] == "ss":
            return self.ss
        raise AssertionError(argv)


def test_modo_tor_apagado_sale_con_2(capsys):
    assert leakcheck.main([], ejecutar=Ejecutor(contador=None)) == 2
    assert "modo Tor no está activo" in capsys.readouterr().out


def test_sin_fugas_sale_con_0(capsys):
    assert leakcheck.main([], ejecutar=Ejecutor(contador=0)) == 0
    assert "0 fugas" in capsys.readouterr().out


def test_paquetes_descartados_son_fuga(capsys):
    assert leakcheck.main([], ejecutar=Ejecutor(contador=4)) == 1
    salida = capsys.readouterr().out
    assert "FUGA" in salida and "4 paquetes" in salida


def test_conexion_directa_es_fuga(capsys):
    ss = 'tcp SYN-SENT 0 1 10.0.2.15:5555 93.184.216.34:443 users:(("curl",pid=1,fd=5))\n'
    assert leakcheck.main([], ejecutar=Ejecutor(contador=0, ss=ss)) == 1
    assert "curl" in capsys.readouterr().out


def test_escribe_estado(tmp_path):
    estado = tmp_path / "leakcheck.json"
    leakcheck.main(["--estado", str(estado)], ejecutar=Ejecutor(contador=2))
    datos = json.loads(estado.read_text(encoding="utf-8"))
    assert datos["modo_tor"] is True
    assert datos["paquetes_descartados"] == 2
    assert datos["limpio"] is False


def test_estado_con_modo_apagado(tmp_path):
    estado = tmp_path / "leakcheck.json"
    leakcheck.main(["--estado", str(estado)], ejecutar=Ejecutor(contador=None))
    assert json.loads(estado.read_text(encoding="utf-8"))["modo_tor"] is False
