"""Tests del espejo parcial del snapshot (ADR-016).

Levanta un "snapshot falso" en localhost y el espejo apuntando a él. No usa la red.

Uso:  python3 -I repro/espejo/test_espejo.py   (sale con 0 solo si todo pasa)
"""
import http.server
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import espejo  # noqa: E402

SNAP = "20260901T000000Z"
DEB = f"/archive/debian/{SNAP}/pool/main/h/hola/hola_1.0_amd64.deb"
INREL = f"/archive/debian-security/{SNAP}/dists/bookworm-security/InRelease"


class SnapshotFalso(http.server.BaseHTTPRequestHandler):
    """Sirve contenido fijo; anota cada petición; simula redirecciones y fallos."""

    ficheros = {}      # ruta -> bytes
    redirigir = {}     # ruta -> ruta destino (como /file/<hash> de snapshot.debian.org)
    fallar = set()     # rutas que devuelven 503 siempre
    peticiones = []

    def do_GET(self):
        SnapshotFalso.peticiones.append(self.path)
        if self.path in self.fallar:
            self.send_error(503)
        elif self.path in self.redirigir:
            self.send_response(302)
            self.send_header("Location", self.redirigir[self.path])
            self.end_headers()
        elif self.path in self.ficheros:
            cuerpo = self.ficheros[self.path]
            self.send_response(200)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
        else:
            self.send_error(404)

    def log_message(self, *a):
        pass


def arrancar(servidor):
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    return servidor


class TestEspejo(unittest.TestCase):
    def setUp(self):
        SnapshotFalso.ficheros = {DEB: b"deb-original", INREL: b"firmado-por-debian",
                                  "/file/abc123": b"contenido-redirigido"}
        SnapshotFalso.redirigir = {}
        SnapshotFalso.fallar = set()
        SnapshotFalso.peticiones = []
        self.origen = arrancar(http.server.ThreadingHTTPServer(("127.0.0.1", 0), SnapshotFalso))
        self.dir = tempfile.mkdtemp()
        self.registro = os.path.join(self.dir, "registro.txt")
        self.datos = os.path.join(self.dir, "datos")
        self.espejo = None

    def tearDown(self):
        for s in (self.espejo, self.origen):
            if s:
                s.shutdown()
                s.server_close()

    def levantar(self, solo_cache=False):
        self.espejo = arrancar(espejo.crear_servidor(
            directorio=self.datos, snapshot=SNAP,
            origen=f"http://127.0.0.1:{self.origen.server_address[1]}",
            solo_cache=solo_cache, puerto=0, registro=self.registro,
            reintentos=2, espera=0))
        return f"http://127.0.0.1:{self.espejo.server_address[1]}"

    def get(self, base, ruta):
        try:
            with urllib.request.urlopen(base + ruta, timeout=10) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            e.close()
            return e.code, b""

    def ficheros_guardados(self):
        out = []
        for raiz, _, nombres in os.walk(self.datos):
            out += [os.path.relpath(os.path.join(raiz, n), self.datos) for n in nombres]
        return sorted(out)

    # --- casos ------------------------------------------------------------------------

    def test_descarga_una_vez_y_luego_sirve_de_cache(self):
        base = self.levantar()
        self.assertEqual(self.get(base, DEB), (200, b"deb-original"))
        SnapshotFalso.fallar.add(DEB)             # el snapshot se cae…
        self.assertEqual(self.get(base, DEB), (200, b"deb-original"))   # …y no importa
        self.assertEqual(SnapshotFalso.peticiones.count(DEB), 1)
        with open(self.registro) as f:
            self.assertEqual([l.split()[0] for l in f], ["DESCARGA", "CACHE"])

    def test_guarda_los_bytes_originales_en_la_misma_ruta(self):
        base = self.levantar()
        self.get(base, INREL)
        with open(os.path.join(self.datos, INREL.lstrip("/")), "rb") as f:
            self.assertEqual(f.read(), b"firmado-por-debian")

    def test_sigue_redirecciones_y_guarda_con_la_ruta_pedida(self):
        SnapshotFalso.redirigir[DEB] = "/file/abc123"
        base = self.levantar()
        self.assertEqual(self.get(base, DEB), (200, b"contenido-redirigido"))
        self.assertEqual(self.ficheros_guardados(), [DEB.lstrip("/")])

    def test_rechaza_rutas_fuera_del_snapshot_anclado(self):
        base = self.levantar()
        for ruta in ("/archive/debian/20990101T000000Z/dists/bookworm/InRelease",
                     "/archive/otra-cosa/" + SNAP + "/x",
                     f"/archive/debian/{SNAP}/../../../etc/passwd",
                     f"/archive/debian/{SNAP}/pool/%2e%2e/%2e%2e/x",
                     "/"):
            self.assertEqual(self.get(base, ruta)[0], 404, ruta)
        self.assertEqual(SnapshotFalso.peticiones, [])

    def test_404_del_snapshot_no_se_guarda(self):
        base = self.levantar()
        ruta = f"/archive/debian/{SNAP}/dists/bookworm/main/binary-amd64/Packages.gz"
        self.assertEqual(self.get(base, ruta)[0], 404)
        self.assertEqual(self.ficheros_guardados(), [])

    def test_fallo_del_snapshot_da_502_y_no_deja_nada(self):
        SnapshotFalso.fallar.add(DEB)
        base = self.levantar()
        self.assertEqual(self.get(base, DEB)[0], 502)
        self.assertEqual(SnapshotFalso.peticiones.count(DEB), 2)   # reintentó
        self.assertEqual(self.ficheros_guardados(), [])

    def test_solo_cache_no_toca_la_red(self):
        base = self.levantar()
        self.get(base, DEB)                        # llena con un espejo normal
        self.espejo.shutdown(); self.espejo.server_close()
        SnapshotFalso.peticiones = []
        base = self.levantar(solo_cache=True)
        self.assertEqual(self.get(base, DEB), (200, b"deb-original"))
        self.assertEqual(self.get(base, INREL)[0], 404)
        self.assertEqual(SnapshotFalso.peticiones, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
