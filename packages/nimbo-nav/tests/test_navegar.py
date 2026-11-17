"""nimbo-navegar-tor: perfil Tor y aviso al usuario (HU-08 CA-3)."""
import json

from nimbo_nav import navegar


def test_preparar_perfil_copia_la_plantilla(tmp_path):
    plantilla = tmp_path / "tor-user.js"
    plantilla.write_text('user_pref("network.proxy.type", 1);\n', encoding="utf-8")
    perfil = tmp_path / "perfil"
    navegar.preparar_perfil(perfil, plantilla)
    assert (perfil / "user.js").read_text(encoding="utf-8") == plantilla.read_text(encoding="utf-8")
    # Si el usuario cambió user.js, se repone la plantilla al abrir de nuevo.
    (perfil / "user.js").write_text("cambiado", encoding="utf-8")
    navegar.preparar_perfil(perfil, plantilla)
    assert "network.proxy.type" in (perfil / "user.js").read_text(encoding="utf-8")


def test_no_abre_si_el_modo_tor_esta_apagado(tmp_path, capsys):
    estado = tmp_path / "leakcheck.json"
    estado.write_text(json.dumps({"modo_tor": False}), encoding="utf-8")
    assert navegar.main([], ruta_estado=estado, lanzar=lambda *a: None) == 2
    salida = capsys.readouterr().out
    # La ISO no trae polkit (medido el 16-nov): nimbo-tor se usa con sudo, como nimbo-red.
    assert "sudo nimbo-tor on" in salida


def test_no_abre_sin_fichero_de_estado(tmp_path, capsys):
    assert navegar.main([], ruta_estado=tmp_path / "no-existe.json", lanzar=lambda *a: None) == 2


# --- El aviso no puede caerse (ISO 16-nov: sin servicio de notificaciones) -----------------
def test_avisar_sin_notify_send_no_se_cae_y_avisa_por_stderr(monkeypatch, capsys):
    def falta(*a, **k):
        raise FileNotFoundError("notify-send")
    monkeypatch.setattr(navegar.subprocess, "run", falta)
    navegar.avisar("fuga de prueba")  # no debe lanzar
    assert "fuga de prueba" in capsys.readouterr().err
