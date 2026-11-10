"""CLI nimbo-update-offline: códigos de salida e instalación sin red (HU-14 CA-1)."""
from nimbo_update_offline import cli


def test_verificar_valido_sale_0(lote, claves, capsys):
    assert cli.main(["verificar", str(lote), "--anillo", str(claves["anillo"])]) == 0
    assert "ACEPTADO" in capsys.readouterr().out


def test_verificar_invalido_sale_1(lote, claves, capsys):
    (lote / "MANIFIESTO.asc").unlink()
    assert cli.main(["verificar", str(lote), "--anillo", str(claves["anillo"])]) == 1
    assert "RECHAZADO" in capsys.readouterr().out


def test_instalar_exige_root(lote, claves, capsys):
    rc = cli.main(["instalar", str(lote), "--anillo", str(claves["anillo"])],
                  es_root=lambda: False, ejecutar=lambda argv: None)
    assert rc == 2
    assert "sudo nimbo-update-offline" in capsys.readouterr().out


def test_instalar_verifica_copias_e_instala_sin_red(lote, claves):
    llamadas = []
    rc = cli.main(["instalar", str(lote), "--anillo", str(claves["anillo"])],
                  es_root=lambda: True, ejecutar=llamadas.append)
    assert rc == 0
    (argv,) = llamadas
    assert argv[:4] == ["apt-get", "install", "--no-download", "-y"]
    debs = argv[4:]
    assert len(debs) == 2
    # Instala las COPIAS verificadas, nunca los ficheros del USB (que podrían cambiar
    # entre la verificación y la instalación).
    assert all(str(lote) not in d for d in debs)


def test_instalar_no_instala_nada_si_se_rechaza(lote, claves):
    (lote / "nimbo-nav_0.1.1-1_all.deb").write_bytes(b"cambiado")
    llamadas = []
    rc = cli.main(["instalar", str(lote), "--anillo", str(claves["anillo"])],
                  es_root=lambda: True, ejecutar=llamadas.append)
    assert rc == 1
    assert llamadas == []
