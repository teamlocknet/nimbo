"""Comprobaciones estáticas de la configuración que instala nimbo-nav (ADR-012).

No sustituyen la medición con pcap en la VM: aseguran que nadie quite por error un
ajuste del que depende RF-NAV-01 / RF-NAV-02.
"""
import json
import os
import re
from pathlib import Path

# Al construir el .deb, pybuild copia las pruebas a otro directorio sin config/ ni debian/:
# debian/rules exporta NIMBO_NAV_SRC con la raíz de la fuente (visto en la VM, 10-nov).
RAIZ = Path(os.environ.get("NIMBO_NAV_SRC") or Path(__file__).resolve().parents[1])
CONFIG = RAIZ / "config"


def _prefs(ruta: Path) -> dict:
    """Lee un fichero de preferencias de Firefox: pref("nombre", valor);"""
    patron = re.compile(r'^\s*(?:user_pref|pref|defaultPref)\("([^"]+)",\s*(.+?)\);\s*$')
    prefs = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        m = patron.match(linea)
        if m:
            prefs[m.group(1)] = json.loads(m.group(2))
    return prefs


# --- RF-NAV-01: políticas del navegador -------------------------------------------------

def _politicas() -> dict:
    return json.loads((CONFIG / "firefox" / "policies.json").read_text(encoding="utf-8"))["policies"]


def test_politicas_desactivan_telemetria_y_servicios():
    p = _politicas()
    for clave in ("DisableTelemetry", "DisableFirefoxStudies", "DisablePocket",
                  "DisableFirefoxAccounts", "DisableFeedbackCommands", "DisableAppUpdate"):
        assert p[clave] is True, clave
    for clave in ("CaptivePortal", "NetworkPrediction", "ExtensionUpdate", "SearchSuggestEnabled"):
        assert p[clave] is False, clave


def test_politicas_bloquean_doh_y_portada():
    p = _politicas()
    assert p["DNSOverHTTPS"] == {"Enabled": False, "Locked": True}
    assert p["FirefoxHome"]["Locked"] is True
    assert not any(v for k, v in p["FirefoxHome"].items() if k != "Locked")
    assert p["Homepage"]["StartPage"] == "none"


def test_politicas_preferencias_bloqueadas():
    prefs = _politicas()["Preferences"]
    esperadas = {
        "browser.safebrowsing.malware.enabled": False,
        "browser.safebrowsing.phishing.enabled": False,
        "browser.safebrowsing.downloads.enabled": False,
        "network.connectivity-service.enabled": False,
        "dom.push.enabled": False,
        "geo.enabled": False,
        "browser.region.update.enabled": False,
        "network.dns.disablePrefetch": True,
        "network.prefetch-next": False,
        "network.http.speculative-parallel-limit": 0,
    }
    for nombre, valor in esperadas.items():
        assert prefs[nombre] == {"Value": valor, "Status": "locked"}, nombre


def test_preferencias_del_sistema_apagan_lo_que_no_cubren_las_politicas():
    prefs = _prefs(CONFIG / "firefox" / "nimbo-nav.js")
    esperadas = {
        "toolkit.telemetry.enabled": False,
        "datareporting.healthreport.uploadEnabled": False,
        "app.normandy.enabled": False,
        "app.shield.optoutstudies.enabled": False,
        "extensions.update.enabled": False,
        "extensions.getAddons.cache.enabled": False,
        "media.gmp-manager.updateEnabled": False,
        "network.trr.mode": 5,
        # Nueva pestaña: sin precarga ni fondos. La precarga de about:newtab descargaba los
        # fondos (newtab-wallpapers-v2) con el navegador en reposo (VM, 10-nov).
        "browser.newtabpage.enabled": False,
        "browser.newtab.preload": False,
        "browser.newtabpage.activity-stream.newtabWallpapers.enabled": False,
    }
    for nombre, valor in esperadas.items():
        assert prefs.get(nombre) == valor, nombre


# --- RF-NAV-02: perfil Tor ---------------------------------------------------------------

def test_perfil_tor_usa_socks_con_dns_remoto_y_sin_fugas():
    prefs = _prefs(CONFIG / "tor" / "tor-user.js")
    esperadas = {
        "network.proxy.type": 1,
        "network.proxy.socks": "127.0.0.1",
        "network.proxy.socks_port": 9050,
        "network.proxy.socks_version": 5,
        "network.proxy.socks_remote_dns": True,
        "network.proxy.no_proxies_on": "",
        "network.proxy.failover_direct": False,
        "media.peerconnection.enabled": False,
        "network.dns.disableIPv6": True,
        "network.trr.mode": 5,
    }
    for nombre, valor in esperadas.items():
        assert prefs.get(nombre) == valor, nombre


# --- RF-NAV-02: tabla nftables del modo Tor ---------------------------------------------

def _nft() -> str:
    """Reglas de la tabla, sin comentarios."""
    texto = (CONFIG / "nftables" / "nimbo-tor.nft").read_text(encoding="utf-8")
    return "\n".join(l.split("#", 1)[0] for l in texto.splitlines())


def test_tabla_falla_cerrada_y_solo_deja_salir_a_tor():
    t = _nft()
    assert "table inet nimbo_tor" in t
    assert "policy drop;" in t
    assert 'oif "lo" accept' in t
    assert re.search(r'meta skuid "debian-tor" (ct mark set 0x[0-9a-f]+ )?accept', t)
    # La última regla de la cadena cuenta y descarta lo que no encaje.
    assert re.search(r'counter name "fugas" drop', t)


def test_tabla_admite_arranque_de_red_sin_contarlo_como_fuga():
    t = _nft()
    assert "udp sport 68 udp dport 67 accept" in t
    assert re.search(r"icmpv6 type \{[^}]*nd-router-solicit[^}]*\}.*ip6 daddr \{ ff02::/16, fe80::/10 \} accept", t)


def test_paquetes_sin_dueno_de_conexiones_de_tor_no_cuentan_como_fuga():
    # Ensayo de la demo (18-nov): al cerrarse una conexión de tor, el RST lo manda el KERNEL,
    # sin proceso dueño, y "meta skuid debian-tor" no lo reconoce: el vigilante lo contaba como
    # fuga (journal "nimbo-fuga … RST"; en el pcap, la conexión de tor con su relé). Igual con
    # los ICMP de error del kernel (observación de #84). Se marca la conexión que abre tor y
    # se aceptan los paquetes de esa conexión aunque no tengan dueño.
    t = _nft()
    marca = re.search(r'meta skuid "debian-tor" ct mark set (0x[0-9a-f]+) accept', t)
    assert marca, "tor debe marcar sus conexiones"
    assert re.search(rf"^\s*ct mark {marca.group(1)} accept", t, re.M)
    # La marca se acepta ANTES de la regla que cuenta y descarta.
    assert t.index(f"ct mark {marca.group(1)} accept") < t.index('counter name "fugas" drop')
    # Nada de aceptar cualquier RST: el de una conexión que no sea de tor sigue siendo fuga.
    assert "tcp flags" not in t


def test_icmp_de_error_a_trafico_entrante_no_cuenta_como_fuga():
    # Observación de #84, medida el 18-nov (pruebas/prueba-icmp-entrante.sh): otro equipo manda
    # UDP a un puerto cerrado y el KERNEL contesta "puerto inalcanzable". Ese ICMP no tiene dueño
    # ni la marca de tor (la conexión la empezó el otro): se descartaba y contaba como fuga. Se
    # acepta solo el ICMP de error en dirección de RESPUESTA a una conexión que vino de fuera.
    t = _nft()
    regla = re.search(r"^\s*ct direction reply ct state related meta l4proto \{ icmp, ipv6-icmp \} accept$", t, re.M)
    assert regla, "falta aceptar los ICMP de error a tráfico entrante"
    assert t.index(regla.group(0).strip()) < t.index('counter name "fugas" drop')


def test_tabla_no_deja_pasar_conexiones_ya_establecidas():
    # Una regla 'ct state established accept' dejaría salir conexiones abiertas antes de
    # activar el modo Tor: sería una fuga silenciosa. El único 'ct state' admitido es el de
    # los ICMP de error a tráfico entrante (prueba anterior).
    estados = re.findall(r"^.*ct state.*$", _nft(), re.M)
    assert all("ct direction reply ct state related meta l4proto" in l for l in estados)
    assert "established" not in _nft()


# --- RNF-01: nada del modo Tor arranca solo ----------------------------------------------

def test_postinst_deshabilita_tor_en_la_primera_instalacion():
    postinst = (RAIZ / "debian" / "postinst").read_text(encoding="utf-8")
    assert "deb-systemd-helper disable tor.service tor@default.service" in postinst
    assert '[ -z "$2" ]' in postinst  # solo en la primera instalación


def test_vigilante_no_se_habilita_nunca():
    unidad = (CONFIG / "systemd" / "nimbo-leakcheck.service").read_text(encoding="utf-8")
    assert "[Install]" not in [l.strip() for l in unidad.splitlines() if not l.startswith("#")]
    assert "ExecStart=/usr/bin/nimbo-leakcheck --vigilar" in unidad
    assert "--no-enable --no-start" in (RAIZ / "debian" / "rules").read_text(encoding="utf-8")


# --- ADR-012 aceptado (#45) ---------------------------------------------------------------

def test_perfil_tor_reduce_la_huella_del_navegador():
    prefs = _prefs(CONFIG / "tor" / "tor-user.js")
    assert prefs.get("privacy.resistFingerprinting") is True
    assert prefs.get("privacy.resistFingerprinting.letterboxing") is True


def _sin_comentarios(ruta):
    return [l.strip() for l in ruta.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.lstrip().startswith("#")]


def test_unidad_modo_tor_falla_cerrada_y_en_orden():
    lineas = _sin_comentarios(CONFIG / "systemd" / "nimbo-modo-tor.service")
    arranque = [l for l in lineas if l.startswith("ExecStart=")]
    parada = [l for l in lineas if l.startswith("ExecStop=")]
    assert arranque == [
        "ExecStart=/usr/sbin/nft -f /usr/share/nimbo-nav/nimbo-tor.nft",
        "ExecStart=/bin/systemctl start tor@default.service",
        "ExecStart=/bin/systemctl start nimbo-leakcheck.service",
    ]
    assert parada == [
        "ExecStop=/bin/systemctl stop nimbo-leakcheck.service",
        "ExecStop=/bin/systemctl stop tor@default.service",
        "ExecStop=/usr/sbin/nft delete table inet nimbo_tor",
    ]
    assert "Type=oneshot" in lineas and "RemainAfterExit=yes" in lineas
    assert "[Install]" not in lineas  # nunca arranca sola
    assert not any("flush ruleset" in l for l in lineas)


def test_lanzador_no_promete_anonimato():
    texto = (CONFIG / "applications" / "nimbo-navegar-tor.desktop").read_text(encoding="utf-8")
    assert "Name=Navegar por Tor\n" in texto
    for prohibido in ("Tor Browser", "anónim", "anonim"):
        assert prohibido not in texto
    assert "no protege frente a la huella del navegador" in texto


# --- Rutas que firefox-esr de Debian lee DE VERDAD (medido en una VM Debian 12, 10-nov) ---
# /etc/firefox/policies y /usr/lib/firefox-esr/defaults/pref NO se aplicaban: Normandy,
# aus5, classify-client y services.addons seguían conectándose con el navegador en reposo.

def _destinos():
    destinos = {}
    for linea in (RAIZ / "debian" / "install").read_text(encoding="utf-8").splitlines():
        if linea.strip():
            origen, destino = linea.split()
            destinos[origen] = destino
    return destinos


def test_politicas_en_el_directorio_distribution_de_firefox_esr():
    assert _destinos()["config/firefox/policies.json"] == "usr/lib/firefox-esr/distribution/"


def test_preferencias_en_etc_firefox_esr_el_mecanismo_de_debian():
    assert _destinos()["config/firefox/nimbo-nav.js"] == "etc/firefox-esr/"


def test_sesion_grafica_activa_el_apagado_de_remote_settings():
    # En Firefox release, services.settings.server solo se respeta con esta variable.
    script = (CONFIG / "x11" / "90nimbo-firefox").read_text(encoding="utf-8")
    assert "export MOZ_REMOTE_SETTINGS_DEVTOOLS=1" in script
    assert _destinos()["config/x11/90nimbo-firefox"] == "etc/X11/Xsession.d/"


# --- Revisión de #59: la limpieza también ocurre si el arranque falla ------------------

def test_unidad_limpia_con_execstoppost_aunque_el_arranque_falle():
    # systemd NO ejecuta ExecStop= si el arranque falló; ExecStopPost= sí.
    lineas = _sin_comentarios(CONFIG / "systemd" / "nimbo-modo-tor.service")
    post = [l for l in lineas if l.startswith("ExecStopPost=")]
    assert post == [
        "ExecStopPost=-/bin/systemctl stop nimbo-leakcheck.service",
        "ExecStopPost=-/bin/systemctl stop tor@default.service",
        "ExecStopPost=-/usr/sbin/nft delete table inet nimbo_tor",
    ]


def test_unidad_no_arranca_con_nimbo_net_activo():
    lineas = _sin_comentarios(CONFIG / "systemd" / "nimbo-modo-tor.service")
    assert "AssertPathExists=!/sys/class/net/wg-nimbo" in lineas
