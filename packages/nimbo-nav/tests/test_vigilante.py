"""El vigilante de fugas no puede morir en silencio (revisión de #46).

Si `ss` (o `nft`) falla, la comprobación no sale del bucle: se escribe un estado
"vigilante": "error" y el navegador lo trata como AVISO. "Sin estado" o "estado viejo"
también son aviso, nunca "limpio".
"""
import json
import subprocess

from nimbo_nav import leakcheck, navegar


def _contador(paquetes):
    return json.dumps({"nftables": [{"counter": {"name": "fugas", "packets": paquetes}}]})


def ejecutor_que_falla_en_ss(argv):
    if argv[0] == "nft":
        return _contador(0)
    raise subprocess.CalledProcessError(1, argv, "", "ss: falló")


def test_una_vuelta_del_vigilante_con_ss_roto_escribe_error(tmp_path):
    ruta = tmp_path / "leakcheck.json"
    leakcheck.vuelta_vigilante(ruta, ejecutar=ejecutor_que_falla_en_ss, ahora=lambda: 1000.0)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["vigilante"] == "error"
    assert "ss" in datos["error"]
    assert datos["actualizado"] == 1000.0


def test_vigilar_no_sale_del_bucle_si_ss_falla(tmp_path):
    ruta = tmp_path / "leakcheck.json"
    vueltas = []

    def dormir(_):
        vueltas.append(1)
        if len(vueltas) >= 3:
            raise KeyboardInterrupt  # cortar la prueba tras 3 vueltas

    try:
        leakcheck.main(["--vigilar", "--estado", str(ruta)], ejecutar=ejecutor_que_falla_en_ss,
                       dormir=dormir)
    except KeyboardInterrupt:
        pass
    assert len(vueltas) == 3  # siguió vivo
    assert json.loads(ruta.read_text(encoding="utf-8"))["vigilante"] == "error"


def test_comprobacion_puntual_con_ss_roto_no_dice_limpio(capsys):
    rc = leakcheck.main([], ejecutar=ejecutor_que_falla_en_ss)
    assert rc == 3
    salida = capsys.readouterr().out
    assert "no se pudo comprobar" in salida
    assert "0 fugas" not in salida


def test_unidad_vigilante_se_reinicia_si_cae():
    from pathlib import Path
    unidad = (Path(__file__).resolve().parents[1] / "config" / "systemd"
              / "nimbo-leakcheck.service").read_text(encoding="utf-8")
    assert "Restart=on-failure" in unidad


# --- Lo que hace el navegador con el estado ----------------------------------------------

BIEN = {"modo_tor": True, "vigilante": "ok", "actualizado": 100.0,
        "paquetes_descartados": 0, "conexiones": []}


def test_estado_bueno_y_reciente_no_avisa():
    assert navegar.motivo_aviso(BIEN, ahora=105.0) is None


def test_sin_estado_es_aviso():
    assert "vigilante" in navegar.motivo_aviso(None, ahora=105.0)


def test_estado_viejo_es_aviso():
    assert "no se actualiza" in navegar.motivo_aviso(BIEN, ahora=100.0 + navegar.MAX_EDAD_S + 1)


def test_vigilante_en_error_es_aviso():
    m = navegar.motivo_aviso(dict(BIEN, vigilante="error", error="ss: falló"), ahora=101.0)
    assert "error" in m


def test_fugas_es_aviso():
    m = navegar.motivo_aviso(dict(BIEN, paquetes_descartados=2), ahora=101.0)
    assert "2 paquetes" in m
