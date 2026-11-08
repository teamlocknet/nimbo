#!/usr/bin/env python3
"""espejo.py — espejo parcial del snapshot anclado de snapshot.debian.org (ADR-016).

Servidor HTTP mínimo (solo biblioteca estándar) que sirve las rutas del snapshot anclado
desde un directorio local. Si una ruta no está, la descarga UNA vez del snapshot, la guarda
tal cual y la sirve. No modifica nada: apt y debootstrap siguen verificando la firma de
Debian y el hash de cada fichero, así que un fichero alterado aquí hace FALLAR el build.

Solo acepta /archive/{debian,debian-security}/<snapshot>/…, que snapshot.debian.org
garantiza inmutable: por eso lo guardado no caduca nunca.

Uso:
  python3 -I repro/espejo/espejo.py --dir ~/.cache/nimbo-espejo [--puerto 8765]
      [--snapshot 20260901T000000Z] [--solo-cache] [--registro registro.txt]
  Por defecto lee el snapshot de iso/live-build/snapshot.env.
  Luego:  NIMBO_ESPEJO=http://127.0.0.1:8765 ./iso/live-build/build-in-container.sh

Registro (--registro): una línea por petición: CACHE | DESCARGA | NO-ENCONTRADO |
RECHAZADA | ERROR, seguida de la ruta. La CI lo usa para saber si hubo descargas.
"""
import argparse
import http.server
import os
import re
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ORIGEN_POR_DEFECTO = "https://snapshot.debian.org"
BLOQUE = 1024 * 1024
RUTA_VALIDA = re.compile(r"^[A-Za-z0-9._+~:/-]+$")
SNAPSHOT_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "iso", "live-build", "snapshot.env")


def leer_snapshot_env(ruta=SNAPSHOT_ENV):
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            m = re.match(r'^NIMBO_SNAPSHOT="?([0-9]{8}T[0-9]{6}Z)"?\s*$', linea.strip())
            if m:
                return m.group(1)
    raise SystemExit(f"ERROR: no encuentro NIMBO_SNAPSHOT en {ruta}")


def ruta_permitida(ruta_http, snapshot):
    """Devuelve la ruta relativa (sin '/' inicial) si es del snapshot anclado; si no, None."""
    ruta = urllib.parse.unquote(urllib.parse.urlsplit(ruta_http).path)
    # live-build pide "<mirror>/" + "/dists/…" → barras repetidas. snapshot.debian.org las
    # trata como una sola; aquí igual, para guardar y pedir al origen la ruta canónica.
    ruta = re.sub(r"/{2,}", "/", ruta)
    if not RUTA_VALIDA.match(ruta):
        return None
    partes = ruta.split("/")
    if any(p in (".", "..") for p in partes):
        return None
    # ['', 'archive', 'debian' | 'debian-security', '<snapshot>', …al menos un segmento]
    if (len(partes) < 5 or partes[0] != "" or partes[1] != "archive"
            or partes[2] not in ("debian", "debian-security") or partes[3] != snapshot
            or partes[-1] == ""):
        return None
    return ruta.lstrip("/")


class Espejo(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, direccion, directorio, snapshot, origen, solo_cache,
                 registro, reintentos, espera):
        super().__init__(direccion, Manejador)
        self.directorio = os.path.abspath(directorio)
        self.snapshot = snapshot
        self.origen = origen.rstrip("/")
        self.solo_cache = solo_cache
        self.registro = registro
        self.reintentos = reintentos
        self.espera = espera
        self._candado = threading.Lock()
        os.makedirs(self.directorio, exist_ok=True)
        # Restos de descargas interrumpidas en una ejecución anterior.
        for raiz, _, nombres in os.walk(self.directorio):
            for n in nombres:
                if ".parcial-" in n:
                    os.remove(os.path.join(raiz, n))

    def anotar(self, tipo, ruta, detalle=""):
        if not self.registro:
            return
        with self._candado, open(self.registro, "a", encoding="utf-8") as f:
            f.write(f"{tipo} {ruta}{(' ' + detalle) if detalle else ''}\n")

    def descargar(self, relativa, destino):
        """Descarga del snapshot a un temporal y lo renombra. Devuelve 200, 404 o 502."""
        url = f"{self.origen}/{relativa}"
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        temporal = f"{destino}.parcial-{os.getpid()}-{threading.get_ident()}"
        motivo = ""
        for intento in range(1, self.reintentos + 1):
            try:
                peticion = urllib.request.Request(url, headers={"User-Agent": "nimbo-espejo"})
                with urllib.request.urlopen(peticion, timeout=120) as r, \
                        open(temporal, "wb") as f:
                    shutil.copyfileobj(r, f, BLOQUE)
                    esperado = r.headers.get("Content-Length")
                if esperado is not None and os.path.getsize(temporal) != int(esperado):
                    raise OSError(f"incompleto: {os.path.getsize(temporal)} de {esperado} bytes")
                os.replace(temporal, destino)
                return 200, ""
            except urllib.error.HTTPError as e:
                e.close()
                if e.code == 404:
                    self._borrar(temporal)
                    return 404, ""
                motivo = f"HTTP {e.code}"
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                motivo = str(getattr(e, "reason", e))
            self._borrar(temporal)
            if intento < self.reintentos:
                time.sleep(self.espera * intento)
        return 502, motivo

    @staticmethod
    def _borrar(ruta):
        try:
            os.remove(ruta)
        except FileNotFoundError:
            pass


class Manejador(http.server.BaseHTTPRequestHandler):
    server_version = "nimbo-espejo"

    def do_GET(self):
        self._servir(con_cuerpo=True)

    def do_HEAD(self):
        self._servir(con_cuerpo=False)

    def _servir(self, con_cuerpo):
        s = self.server
        relativa = ruta_permitida(self.path, s.snapshot)
        if relativa is None:
            s.anotar("RECHAZADA", self.path)
            self.send_error(404)
            return
        destino = os.path.join(s.directorio, relativa)
        if os.path.isfile(destino):
            s.anotar("CACHE", relativa)
        elif s.solo_cache:
            s.anotar("NO-ENCONTRADO", relativa, "(solo-cache)")
            self.send_error(404)
            return
        else:
            codigo, motivo = s.descargar(relativa, destino)
            if codigo == 404:
                s.anotar("NO-ENCONTRADO", relativa)
                self.send_error(404)
                return
            if codigo != 200:
                s.anotar("ERROR", relativa, motivo)
                self.send_error(502, f"snapshot no disponible: {motivo}")
                return
            s.anotar("DESCARGA", relativa)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(os.path.getsize(destino)))
        self.end_headers()
        if con_cuerpo:
            with open(destino, "rb") as f:
                shutil.copyfileobj(f, self.wfile, BLOQUE)

    def log_message(self, *a):
        pass   # el registro propio (--registro) es el que cuenta


def crear_servidor(directorio, snapshot, origen=ORIGEN_POR_DEFECTO, solo_cache=False,
                   puerto=8765, registro=None, reintentos=5, espera=5, escuchar="127.0.0.1"):
    return Espejo((escuchar, puerto), directorio, snapshot, origen, solo_cache,
                  registro, reintentos, espera)


def main():
    p = argparse.ArgumentParser(description="Espejo parcial del snapshot anclado (ADR-016).")
    p.add_argument("--dir", required=True, help="directorio donde se guardan los ficheros")
    p.add_argument("--puerto", type=int, default=8765)
    p.add_argument("--snapshot", help="timestamp (por defecto, el de iso/live-build/snapshot.env)")
    p.add_argument("--origen", default=ORIGEN_POR_DEFECTO)
    p.add_argument("--solo-cache", action="store_true", help="no descargar nunca: lo que falte → 404")
    p.add_argument("--registro", help="fichero donde anotar cada petición")
    a = p.parse_args()

    snapshot = a.snapshot or leer_snapshot_env()
    servidor = crear_servidor(a.dir, snapshot, a.origen, a.solo_cache, a.puerto, a.registro)
    modo = "solo caché" if a.solo_cache else f"se llena desde {a.origen}"
    print(f"espejo listo en http://127.0.0.1:{servidor.server_address[1]} "
          f"(snapshot {snapshot}, {modo}, dir {servidor.directorio})", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
