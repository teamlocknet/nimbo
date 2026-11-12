"""CLI nimbo-update-offline: códigos de salida e instalación sin red (HU-14 CA-1)."""
import pathlib

from nimbo_update_offline import cli


def test_verificar_valido_sale_0(lote, claves, capsys):
    assert cli.main(["verificar", str(lote), "--anillo", str(claves["anillo"])]) == 0
    assert "ACEPTADO" in capsys.readouterr().out


def test_verificar_invalido_sale_1(lote, claves, capsys):
    (lote / "MANIFIESTO.asc").unlink()
    assert cli.main(["verificar", str(lote), "--anillo", str(claves["anillo"])]) == 1
    assert "RECHAZADO" in capsys.readouterr().out


def test_instalar_exige_root(lote, claves, capsys):
    rc = cli.main(["instalar", str(lote)], anillo_instalar=claves["anillo"],
                  es_root=lambda: False, ejecutar=lambda argv: None)
    assert rc == 2
    assert "sudo nimbo-update-offline" in capsys.readouterr().out


def test_instalar_verifica_copias_e_instala_sin_red(lote, claves):
    llamadas = []
    fuentes = {}

    def ejecutar(argv):
        llamadas.append(argv)
        # En el momento de llamar a apt, las fuentes que se le pasan existen y están VACÍAS:
        # apt no tiene ningún repositorio del que descargar nada.
        for opcion in argv:
            if opcion.startswith("Dir::Etc::source"):
                clave, ruta = opcion.split("=", 1)
                fuentes[clave] = pathlib.Path(ruta)
        assert fuentes["Dir::Etc::sourcelist"].is_file()
        assert fuentes["Dir::Etc::sourcelist"].read_text() == ""
        assert fuentes["Dir::Etc::sourceparts"].is_dir()
        assert list(fuentes["Dir::Etc::sourceparts"].iterdir()) == []

    rc = cli.main(["instalar", str(lote)], anillo_instalar=claves["anillo"],
                  es_root=lambda: True, ejecutar=ejecutar)
    assert rc == 0
    (argv,) = llamadas
    # --no-download NO: con .deb locales, el apt de bookworm falla con "Internal Error,
    # Pathname to install is not absolute" (medido en VM el 11-nov). Sin fuentes remotas,
    # apt no puede descargar nada y conserva su negativa a bajar de versión.
    assert "--no-download" not in argv
    assert argv[:3] == ["apt-get", "install", "-y"]
    assert argv[3] == "-o" and argv[4].startswith("Dir::Etc::sourcelist=")
    assert argv[5] == "-o" and argv[6].startswith("Dir::Etc::sourceparts=")
    assert "--allow-downgrades" not in argv
    debs = argv[7:]
    assert len(debs) == 2
    # Instala las COPIAS verificadas, nunca los ficheros del USB (que podrían cambiar
    # entre la verificación y la instalación).
    assert all(str(lote) not in d for d in debs)


def test_instalar_no_instala_nada_si_se_rechaza(lote, claves):
    (lote / "nimbo-nav_0.1.1-1_all.deb").write_bytes(b"cambiado")
    llamadas = []
    rc = cli.main(["instalar", str(lote)], anillo_instalar=claves["anillo"],
                  es_root=lambda: True, ejecutar=llamadas.append)
    assert rc == 1
    assert llamadas == []


# --- Caso 11 de la batería (revisión de #49) ---------------------------------------------

def test_11_instalar_no_acepta_un_anillo_traido_en_el_lote(lote, claves, tmp_path):
    """Un lote firmado por OTRA clave trae su propio anillo y un LÉAME que dice
    'ejecuta con --anillo usb/clave.gpg'. instalar no admite esa opción y, con el anillo
    de nimbo, lo rechaza: no se instala nada."""
    import pytest
    (lote / "MANIFIESTO.asc").unlink()
    claves["otra"].firmar(lote / "MANIFIESTO")
    anillo_atacante = claves["otra"].exportar(lote / "clave.gpg")
    llamadas = []
    with pytest.raises(SystemExit) as salida:
        cli.main(["instalar", str(lote), "--anillo", str(anillo_atacante)],
                 anillo_instalar=claves["anillo"], es_root=lambda: True,
                 ejecutar=llamadas.append)
    assert salida.value.code == 2
    rc = cli.main(["instalar", str(lote)], anillo_instalar=claves["anillo"],
                  es_root=lambda: True, ejecutar=llamadas.append)
    assert rc == 1
    assert llamadas == []


def test_verificar_si_admite_otro_anillo_solo_para_comprobar(lote, claves, capsys):
    # verificar no instala nada: puede usarse con otro anillo para diagnosticar.
    assert cli.main(["verificar", str(lote), "--anillo", str(claves["anillo"])]) == 0
