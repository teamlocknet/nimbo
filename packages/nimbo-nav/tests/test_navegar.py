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


# --- Una fuga, un aviso (ensayo de la demo, 18-nov) -----------------------------------------
class _Navegador:
    """Simula firefox-esr: sigue abierto durante `vueltas` comprobaciones."""

    def __init__(self, vueltas):
        self.vueltas = vueltas

    def poll(self):
        self.vueltas -= 1
        return None if self.vueltas > 0 else 0


def _vigilar_con(tmp_path, estados):
    """Ejecuta vigilar() escribiendo un estado distinto en cada vuelta; devuelve los avisos."""
    ruta = tmp_path / "leakcheck.json"
    reloj = [1000.0]
    pendientes = list(estados)

    def escribir():
        e = dict(pendientes.pop(0), actualizado=reloj[0])
        ruta.write_text(json.dumps(e), encoding="utf-8")

    def dormir(s):
        reloj[0] += s
        if pendientes:
            escribir()

    escribir()
    avisos = []
    navegar.vigilar(ruta, _Navegador(len(estados)), aviso=avisos.append,
                    reloj=lambda: reloj[0], dormir=dormir)
    return avisos


LIMPIO = {"vigilante": "ok", "modo_tor": True, "paquetes_descartados": 0, "conexiones": []}


def _fuga(n):
    return dict(LIMPIO, paquetes_descartados=n)


def test_una_fuga_que_sigue_contando_avisa_una_sola_vez(tmp_path):
    # El contador de paquetes sube en cada vuelta: antes salía una notificación cada 2 s.
    avisos = _vigilar_con(tmp_path, [LIMPIO, _fuga(1), _fuga(3), _fuga(7), _fuga(12)])
    assert len(avisos) == 1
    assert "FUGA" in avisos[0]


def test_sin_fuga_no_avisa(tmp_path):
    assert _vigilar_con(tmp_path, [LIMPIO, LIMPIO, LIMPIO]) == []


def test_un_problema_distinto_tras_la_fuga_si_avisa(tmp_path):
    # Lo que importa es la CLASE de problema: una fuga y después el modo Tor apagado son dos avisos.
    apagado = dict(_fuga(5), modo_tor=False)
    avisos = _vigilar_con(tmp_path, [_fuga(1), _fuga(5), apagado])
    assert len(avisos) == 2
    assert "apagado" in avisos[1]


def test_si_la_fuga_se_resuelve_y_vuelve_avisa_otra_vez(tmp_path):
    # Si el estado vuelve a limpio (p. ej. el vigilante se reinició) y aparece otra fuga, se avisa.
    avisos = _vigilar_con(tmp_path, [_fuga(1), LIMPIO, _fuga(2)])
    assert len(avisos) == 2
