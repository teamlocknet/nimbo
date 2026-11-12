"""WireGuard entre dos pares preparados; nunca configura la red fisica."""
from __future__ import annotations

import argparse
import base64
import contextlib
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import time
from pathlib import Path

INTERFAZ = "wg-nimbo"
UNIDAD_TOR = "nimbo-modo-tor.service"
CAMPOS = {"version", "address", "peer_address", "peer_public_key", "endpoint",
          "endpoint_port", "listen_port", "timeout"}


class ErrorNet(Exception):
    """Diagnostico publico: nunca contiene datos privados ni stderr del sistema."""


def ejecutar_sistema(argv):
    executable = shutil.which(argv[0], path="/usr/sbin:/usr/bin:/sbin:/bin")
    if not executable:
        raise ErrorNet("falta herramienta: " + argv[0])
    try:
        return subprocess.run([executable, *argv[1:]], check=True, capture_output=True,
                              text=True, timeout=10,
                              env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"}).stdout
    except subprocess.TimeoutExpired:
        raise ErrorNet("una herramienta del sistema excedio su espera") from None


def directorio(path, uid):
    st = path.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != uid or stat.S_IMODE(st.st_mode) != 0o700:
        raise ErrorNet("directorio de configuracion/estado requiere propietario y modo 0700")


def leer(path, uid, privado=True):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "r", encoding="utf-8") as f:
        st = os.fstat(f.fileno())
        mode = stat.S_IMODE(st.st_mode)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != uid or st.st_nlink != 1
                or (mode != 0o600 if privado else mode & 0o022)):
            raise ErrorNet("archivo de configuracion/estado con permisos o propietario inseguros")
        data = f.read(16385)
        if len(data) > 16384:
            raise ErrorNet("archivo de configuracion/estado demasiado grande")
        return data


def pares_unicos(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ErrorNet("campos JSON duplicados")
        result[k] = v
    return result


def objeto(data):
    value = json.loads(data, object_pairs_hook=pares_unicos)
    if not isinstance(value, dict):
        raise ErrorNet("se esperaba un objeto JSON")
    return value


def clave_valida(value):
    if not isinstance(value, str):
        raise ErrorNet("clave WireGuard invalida")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise ErrorNet("clave WireGuard invalida") from None
    if len(raw) != 32 or not any(raw) or base64.b64encode(raw).decode() != value:
        raise ErrorNet("clave WireGuard invalida")


def perfil(config_dir, uid):
    directorio(config_dir, uid)
    data = leer(config_dir / "perfil.json", uid)
    p = objeto(data)
    if set(p) != CAMPOS or type(p["version"]) is not int or p["version"] != 1:
        raise ErrorNet("perfil version 1 con campos desconocidos o ausentes")
    for k in ["address", "peer_address", "endpoint"]:
        if not isinstance(p[k], str):
            raise ErrorNet("las direcciones deben ser texto IPv4")
        a = ipaddress.IPv4Address(p[k])
        if a.is_multicast or a.is_unspecified or a.is_loopback or str(a) == "255.255.255.255":
            raise ErrorNet("direccion IPv4 no utilizable")
        if k != "endpoint" and not any(a in ipaddress.IPv4Network(net) for net in
                                      ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]):
            raise ErrorNet("el tunel requiere direcciones privadas IPv4")
        p[k] = str(a)
    if len({p["address"], p["peer_address"], p["endpoint"]}) != 3:
        raise ErrorNet("direcciones del tunel y endpoint deben ser distintas")
    for k in ["listen_port", "endpoint_port"]:
        if type(p[k]) is not int or not 1024 <= p[k] <= 65535:
            raise ErrorNet("puerto fuera de 1024..65535")
    if type(p["timeout"]) is not int or not 1 <= p["timeout"] <= 300:
        raise ErrorNet("espera fuera de 1..300 segundos")
    clave_valida(p["peer_public_key"])
    key = leer(config_dir / "private.key", uid).strip()
    clave_valida(key)
    digest = hashlib.sha256((json.dumps(p, sort_keys=True) + key).encode()).hexdigest()
    return p, digest


def lista(run, argv):
    value = json.loads(run(argv))
    if not isinstance(value, list) or any(not isinstance(v, dict) for v in value):
        raise ErrorNet("respuesta de red invalida")
    return value


def enlace(run):
    return next((x for x in lista(run, ["ip", "-j", "link", "show"])
                 if x.get("ifname") == INTERFAZ), None)


def sin_tor(run):
    props = dict(line.split("=", 1) for line in run(
        ["systemctl", "show", UNIDAD_TOR, "--property=LoadState", "--property=ActiveState"]
    ).splitlines() if "=" in line)
    if props.get("LoadState") not in ["loaded", "not-found"] or props.get("ActiveState") != "inactive":
        raise ErrorNet("Tor activo, en transicion o sin estado fiable; apaga nimbo-tor antes de join")
    tables = objeto(run(["nft", "-j", "list", "tables"]))
    if not isinstance(tables.get("nftables"), list):
        raise ErrorNet("no se pudo determinar la politica nftables")
    if any(t.get("table", {}).get("name") == "nimbo_tor" and
           t.get("table", {}).get("family") == "inet" for t in tables["nftables"]):
        raise ErrorNet("tabla Tor presente; apaga nimbo-tor antes de join")


def comprobar_red(run, red_dir, p, uid):
    if red_dir.exists() or red_dir.is_symlink():
        st = red_dir.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != uid or stat.S_IMODE(st.st_mode) & 0o022:
            raise ErrorNet("estado de nimbo-red inseguro")
    try:
        iface = leer(red_dir / "interfaz", uid, privado=False).strip()
    except FileNotFoundError:
        raise ErrorNet("primero activa la red: sudo nimbo-red on") from None
    if not re.fullmatch(r"(?:en|eth)[a-z0-9]{0,13}", iface):
        raise ErrorNet("interfaz de nimbo-red invalida")
    addresses = lista(run, ["ip", "-j", "address", "show", "dev", iface])
    if not any("UP" in x.get("flags", []) and any(a.get("family") == "inet" and
               a.get("scope") == "global" for a in x.get("addr_info", [])) for x in addresses):
        raise ErrorNet("sin IPv4 fisica; usa sudo nimbo-red on")
    routes = lista(run, ["ip", "-j", "route", "get", p["endpoint"]])
    if not routes or routes[0].get("dev") != iface:
        raise ErrorNet("endpoint sin ruta por la interfaz de nimbo-red")
    for route in lista(run, ["ip", "-j", "route", "show", "table", "all"]):
        dst = route.get("dst", "default")
        if dst == "default" or ":" in dst:
            continue
        network = ipaddress.IPv4Network(dst, strict=False)
        if any(ipaddress.IPv4Address(p[k]) in network for k in ["address", "peer_address"]):
            raise ErrorNet("direccion del tunel en conflicto con una ruta existente")


@contextlib.contextmanager
def bloqueo(run_dir, uid):
    run_dir.mkdir(mode=0o700, exist_ok=True)
    directorio(run_dir, uid)
    fd = os.open(run_dir / "operacion.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != uid or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1:
            raise ErrorNet("bloqueo inseguro")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ErrorNet("otra operacion nimbo-net esta en curso") from None
        yield
    finally:
        os.close(fd)


def guardar(path, value):
    temp = path.with_name(".estado-" + secrets.token_hex(8))
    try:
        fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(value, f)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def estado(run_dir, uid):
    path = run_dir / "estado.json"
    try:
        s = objeto(leer(path, uid))
    except FileNotFoundError:
        return None
    if (set(s) != {"alias", "ifindex", "perfil"} or type(s["ifindex"]) is not int
            or not isinstance(s["alias"], str) or not re.fullmatch(r"nimbo-net:[0-9a-f]{32}", s["alias"])
            or not isinstance(s["perfil"], str) or not re.fullmatch(r"[0-9a-f]{64}", s["perfil"])):
        raise ErrorNet("estado local invalido; no se eliminaran recursos")
    return s


def propio(link, s):
    return s and link and link.get("ifindex") == s["ifindex"] and link.get("ifalias") == s["alias"]


def retirar(run, run_dir, s):
    link = enlace(run)
    if link:
        if not propio(link, s):
            raise ErrorNet("wg-nimbo ajena o identidad cambiada; no se elimina")
        run(["ip", "link", "delete", "dev", INTERFAZ])
    (run_dir / "estado.json").unlink(missing_ok=True)


def conectar(run, p, dormir):
    # Numero de intentos y tiempos de herramientas acotados; ambos pares deben
    # activar join dentro de la ventana anunciada por el operador.
    for _ in range(p["timeout"]):
        sin_tor(run)
        ping = False
        try:
            run(["ping", "-n", "-c", "1", "-W", "1", "-I", INTERFAZ, p["peer_address"]])
            ping = True
        except subprocess.CalledProcessError:
            pass
        handshakes = run(["wg", "show", INTERFAZ, "latest-handshakes"])
        for line in handshakes.splitlines():
            fields = line.split()
            if len(fields) == 2 and fields[0] == p["peer_public_key"] and int(fields[1]) > 0 and ping:
                sin_tor(run)
                return
        dormir(1)
    raise ErrorNet("timeout sin handshake y trafico; activa join en ambos equipos y revisa perfiles")


def join(run, config_dir, run_dir, red_dir, uid, dormir, imprimir):
    p, digest = perfil(config_dir, uid)
    sin_tor(run)
    link = enlace(run)
    s = estado(run_dir, uid)
    if link:
        if not propio(link, s) or s["perfil"] != digest:
            raise ErrorNet("wg-nimbo ya existe o el perfil cambio; revisa status/leave")
        conectar(run, p, dormir)
        imprimir("nimbo-net: conectado (tunel existente comprobado)")
        return
    comprobar_red(run, red_dir, p, uid)
    token = "nimbo-net:" + secrets.token_hex(16)
    # Alias en la propia creacion: si add falla nunca se elimina una interfaz ajena.
    run(["ip", "link", "add", "dev", INTERFAZ, "alias", token, "type", "wireguard"])
    try:
        link = enlace(run)
        if not link or link.get("ifalias") != token:
            raise ErrorNet("no se pudo identificar la interfaz creada")
        s = {"alias": token, "ifindex": link["ifindex"], "perfil": digest}
        guardar(run_dir / "estado.json", s)
        sin_tor(run)
        run(["wg", "set", INTERFAZ, "listen-port", str(p["listen_port"]),
             "private-key", str(config_dir / "private.key"), "peer", p["peer_public_key"],
             "endpoint", p["endpoint"] + ":" + str(p["endpoint_port"]),
             "allowed-ips", p["peer_address"] + "/32", "persistent-keepalive", "0"])
        run(["ip", "address", "add", p["address"] + "/32", "dev", INTERFAZ])
        run(["ip", "link", "set", "dev", INTERFAZ, "up"])
        run(["ip", "route", "add", p["peer_address"] + "/32", "dev", INTERFAZ, "src", p["address"]])
        imprimir("nimbo-net: esperando al par; ejecuta join en ambos equipos")
        conectar(run, p, dormir)
        if not propio(enlace(run), s):
            raise ErrorNet("la identidad de la interfaz cambio durante join")
    except (Exception, KeyboardInterrupt):
        # Solo retirar si la identidad coincide; un fallo de limpieza conserva
        # estado para permitir leave/revision, sin anunciar silencio falso.
        if s and s.get("alias") == token:
            retirar(run, run_dir, s)
        else:
            current = enlace(run)
            if current and current.get("ifalias") == token:
                run(["ip", "link", "delete", "dev", INTERFAZ])
        raise
    imprimir("nimbo-net: conectado; handshake y trafico al par comprobados")


def main(argv=None, ejecutar=ejecutar_sistema, config_dir=Path("/etc/nimbo-net"),
         run_dir=Path("/run/nimbo-net"), red_dir=Path("/run/nimbo-red"), uid=0,
         es_root=lambda: os.geteuid() == 0, dormir=time.sleep, imprimir=print):
    parser = argparse.ArgumentParser(prog="nimbo-net", description=__doc__)
    parser.add_argument("accion", choices=["join", "leave", "status"])
    args = parser.parse_args(argv)
    if args.accion != "status" and not es_root():
        imprimir("nimbo-net: necesita privilegios; usa sudo nimbo-net " + args.accion)
        return 2
    try:
        if args.accion == "status":
            link = enlace(ejecutar)
            imprimir("nimbo-net: wg-nimbo presente; usa join para comprobar conectividad" if link
                     else "nimbo-net: inactivo")
            return 0
        with bloqueo(run_dir, uid):
            if args.accion == "leave":
                retirar(ejecutar, run_dir, estado(run_dir, uid))
                imprimir("nimbo-net: tunel retirado; red fisica sin cambios")
            else:
                join(ejecutar, config_dir, run_dir, red_dir, uid, dormir, imprimir)
        return 0
    except KeyboardInterrupt:
        imprimir("nimbo-net: operacion interrumpida; revisa status y usa leave si quedan recursos")
        return 130
    except ErrorNet as e:
        imprimir("nimbo-net: " + str(e))
        return 1
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        imprimir("nimbo-net: fallo de configuracion o sistema; no se muestran datos privados. Revisa status/leave")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
