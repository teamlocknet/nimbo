"""Contrato de nimbo-net: no modifica la red real del anfitrion."""
import base64
import json
import os
import secrets
import subprocess
import tempfile
import unittest
from pathlib import Path

from nimbo_net import cli


class Sistema:
    def __init__(self):
        self.calls = []
        self.link = None
        self.tor = "inactive"
        self.tabla = False
        self.ping = True
        self.handshake = True
        self.fail = None
        self.ajeno = False

    def __call__(self, argv):
        self.calls.append(list(argv))
        if self.fail and argv[:len(self.fail)] == self.fail:
            raise subprocess.CalledProcessError(1, argv, stderr="fallo simulado")
        if argv[:3] == ["ip", "-j", "link"]:
            return json.dumps([self.link] if self.link else [])
        if argv[:2] == ["systemctl", "show"]:
            return "LoadState=loaded\nActiveState=" + self.tor + "\n"
        if argv[:4] == ["nft", "-j", "list", "tables"]:
            return json.dumps({"nftables": [{"table": {"family": "inet", "name": "nimbo_tor"}}] if self.tabla else []})
        if argv[:4] == ["ip", "-j", "address", "show"]:
            return json.dumps([{"flags": ["UP"], "addr_info": [{"family": "inet", "scope": "global", "local": "192.0.2.1"}]}])
        if argv[:4] == ["ip", "-j", "route", "get"]:
            return json.dumps([{"dev": "eth0", "prefsrc": "192.0.2.1"}])
        if argv[:4] == ["ip", "-j", "route", "show"]:
            return "[]"
        if argv[:3] == ["ip", "link", "add"]:
            if self.link is not None:
                raise subprocess.CalledProcessError(2, argv, stderr="EEXIST")
            # Bookworm/iproute2: add no aplica ifalias aunque reciba alias.
            self.link = {"ifname": "wg-nimbo", "ifindex": 20}
        if argv[:6] == ["ip", "link", "set", "dev", "wg-nimbo", "alias"]:
            self.link["ifalias"] = argv[6]
        if argv[:3] == ["ip", "link", "delete"]:
            self.link = None
        if argv[:1] == ["ping"]:
            if not self.ping:
                raise subprocess.CalledProcessError(1, argv)
        if argv[:3] == ["wg", "show", "wg-nimbo"]:
            if self.ajeno:
                self.link["ifalias"] = "otro"
            return self.public + "\t" + ("1" if self.handshake else "0") + "\n"
        return ""


class PruebasNet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "config"
        self.config.mkdir(mode=0o700)
        self.runtime = self.root / "run"
        self.red = self.root / "nimbo-red"
        self.red.mkdir(mode=0o700)
        (self.red / "interfaz").write_text("eth0\n")
        # Identidades sinteticas generadas en cada prueba, nunca versionadas.
        (self.config / "private.key").write_text(base64.b64encode(secrets.token_bytes(32)).decode() + "\n")
        (self.config / "private.key").chmod(0o600)
        self.profile = {"version": 1, "address": "10.90.0.1", "peer_address": "10.90.0.2",
                        "peer_public_key": base64.b64encode(secrets.token_bytes(32)).decode(),
                        "endpoint": "192.0.2.2", "endpoint_port": 51820,
                        "listen_port": 51820, "timeout": 1}
        self.save()
        self.sys = Sistema()
        self.sys.public = self.profile["peer_public_key"]
        self.output = []

    def save(self):
        p = self.config / "perfil.json"
        p.write_text(json.dumps(self.profile))
        p.chmod(0o600)

    def main(self, action="join", root=True):
        return cli.main([action], ejecutar=self.sys, config_dir=self.config,
                        run_dir=self.runtime, red_dir=self.red, uid=os.getuid(),
                        es_root=lambda: root, dormir=lambda _: None,
                        imprimir=self.output.append)

    def test_join_configura_solo_tunel(self):
        self.assertEqual(self.main(), 0, self.output)
        self.assertEqual(self.sys.link["ifname"], "wg-nimbo")
        self.assertTrue((self.runtime / "estado.json").exists())
        commands = self.sys.calls
        self.assertTrue(any(c[:3] == ["wg", "set", "wg-nimbo"] for c in commands))
        self.assertTrue(any(c[:3] == ["ip", "route", "add"] and "10.90.0.2/32" in c for c in commands))
        self.assertFalse(any(c[0] in ["dhclient", "sysctl", "nimbo-red"] for c in commands))
        self.assertFalse(any("default" in c or "ruleset" in c for c in commands))

    def test_fallo_set_alias_no_deja_interfaz(self):
        self.sys.fail = ["ip", "link", "set", "dev", "wg-nimbo", "alias"]
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)
        self.assertFalse((self.runtime / "estado.json").exists())

    def test_fallo_lectura_tras_add_no_deja_interfaz(self):
        original = Sistema.__call__
        def execute(system, argv):
            if argv[:3] == ["ip", "-j", "link"] and system.link:
                raise subprocess.CalledProcessError(1, argv)
            return original(system, argv)
        from unittest.mock import patch
        with patch.object(Sistema, "__call__", execute):
            self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)
        self.assertFalse((self.runtime / "estado.json").exists())

    def test_add_eexist_no_borra_interfaz_surgida_en_carrera(self):
        original = Sistema.__call__
        def execute(system, argv):
            if argv[:3] == ["ip", "link", "add"]:
                system.link = {"ifname": "wg-nimbo", "ifindex": 30, "ifalias": "ajena"}
            return original(system, argv)
        from unittest.mock import patch
        with patch.object(Sistema, "__call__", execute):
            self.assertEqual(self.main(), 1)
        self.assertEqual(self.sys.link["ifalias"], "ajena")
        self.assertFalse(any(c[:3] == ["ip", "link", "delete"] for c in self.sys.calls))

    def test_leave_solo_elimina_interfaz_propia(self):
        self.assertEqual(self.main(), 0)
        self.sys.calls.clear()
        self.assertEqual(self.main("leave"), 0)
        self.assertIsNone(self.sys.link)
        self.assertFalse((self.runtime / "estado.json").exists())
        self.assertEqual([c for c in self.sys.calls if c[:2] == ["ip", "link"]], [["ip", "link", "delete", "dev", "wg-nimbo"]])
        self.assertTrue((self.red / "interfaz").exists())

    def test_leave_repetido(self):
        self.assertEqual(self.main("leave"), 0)
        self.assertEqual(self.main("leave"), 0)

    def test_join_repetido_no_duplica(self):
        self.assertEqual(self.main(), 0)
        self.assertEqual(self.main(), 0)
        self.assertEqual(sum(c[:3] == ["ip", "link", "add"] for c in self.sys.calls), 1)

    def test_sin_root_no_modifica(self):
        self.assertEqual(self.main(root=False), 2)
        self.assertEqual(self.sys.calls, [])

    def test_sin_red_indica_nimbo_red(self):
        (self.red / "interfaz").unlink()
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)
        self.assertIn("nimbo-red on", " ".join(self.output))

    def test_tor_activo_o_transicion(self):
        for state in ["active", "activating", "deactivating", "failed"]:
            self.sys.tor = state
            self.assertEqual(self.main(), 1, state)
            self.assertIsNone(self.sys.link)

    def test_tabla_tor_aunque_unidad_inactiva(self):
        self.sys.tabla = True
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)

    def test_error_nft_no_significa_tor_apagado(self):
        self.sys.fail = ["nft"]
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)

    def test_interfaz_ajena_no_se_borra(self):
        self.sys.link = {"ifname": "wg-nimbo", "ifindex": 30, "ifalias": "ajena"}
        self.assertEqual(self.main(), 1)
        self.assertEqual(self.main("leave"), 1)
        self.assertEqual(self.sys.link["ifalias"], "ajena")

    def test_timeout_limpia(self):
        self.sys.ping = False
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)
        self.assertFalse((self.runtime / "estado.json").exists())

    def test_ping_sin_handshake_no_es_exito(self):
        self.sys.handshake = False
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)

    def test_fallo_wg_limpia_sin_mostrar_stderr(self):
        self.sys.fail = ["wg", "set"]
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)
        self.assertNotIn("fallo simulado", " ".join(self.output))

    def test_clave_no_sale_en_argumentos_o_salida(self):
        private = (self.config / "private.key").read_text().strip()
        self.assertEqual(self.main(), 0)
        self.assertNotIn(private, repr(self.sys.calls) + repr(self.output))

    def test_permisos_debiles(self):
        (self.config / "private.key").chmod(0o644)
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)

    def test_symlink_de_clave(self):
        k = self.config / "private.key"
        k.rename(self.config / "otra")
        k.symlink_to(self.config / "otra")
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)

    def test_perfil_rechaza_ruta_por_defecto_y_campos_extra(self):
        self.profile["PostUp"] = "no ejecutar"
        self.save()
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)

    def test_endpoint_no_puede_ser_peer_interno(self):
        self.profile["endpoint"] = self.profile["peer_address"]
        self.save()
        self.assertEqual(self.main(), 1)

    def test_perfil_invalido(self):
        for field, value in [("address", "::1"), ("peer_address", "0.0.0.0/0"),
                             ("endpoint", "ejemplo.invalid"), ("listen_port", True),
                             ("timeout", 0), ("peer_public_key", "invalida")]:
            original = self.profile[field]
            self.profile[field] = value
            self.save()
            self.assertEqual(self.main(), 1, field)
            self.assertIsNone(self.sys.link)
            self.profile[field] = original

    def test_tor_activado_tras_crear_interfaz_limpia(self):
        original = Sistema.__call__
        def execute(system, argv):
            result = original(system, argv)
            if argv[:3] == ["ip", "link", "add"]:
                system.tor = "activating"
            return result
        from unittest.mock import patch
        with patch.object(Sistema, "__call__", execute):
            self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)

    def test_operacion_concurrente_rechazada(self):
        import fcntl
        self.runtime.mkdir(mode=0o700)
        lock = self.runtime / "operacion.lock"
        lock.touch(mode=0o600)
        with lock.open("r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.main(), 1)
        self.assertEqual(self.sys.calls, [])

    def test_fallo_limpieza_conserva_estado(self):
        self.assertEqual(self.main(), 0)
        self.sys.fail = ["ip", "link", "delete"]
        self.assertEqual(self.main("leave"), 1)
        self.assertTrue((self.runtime / "estado.json").exists())
        self.assertIsNotNone(self.sys.link)

    def test_identidad_cambiada_durante_join_no_se_borra(self):
        self.sys.ajeno = True
        self.assertEqual(self.main(), 1)
        self.assertEqual(self.sys.link["ifalias"], "otro")

    def test_directorio_config_inseguro(self):
        self.config.chmod(0o755)
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)

    def test_hardlink_de_clave_se_rechaza(self):
        os.link(self.config / "private.key", self.root / "copia")
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)

    def test_json_duplicado(self):
        (self.config / "perfil.json").write_text('{"version":1,"version":1}')
        self.assertEqual(self.main(), 1)

    def test_estado_obsoleto_sin_interfaz_se_retira(self):
        self.assertEqual(self.main(), 0)
        self.sys.link = None
        self.assertEqual(self.main("leave"), 0)
        self.assertFalse((self.runtime / "estado.json").exists())

    def test_endpoint_entero_se_rechaza(self):
        self.profile["endpoint"] = 3221225986
        self.save()
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)

    def test_directorio_red_escribible_se_rechaza(self):
        self.red.chmod(0o777)
        self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)

    def test_status_sin_root_no_activa(self):
        self.assertEqual(self.main("status", root=False), 0)
        self.assertIsNone(self.sys.link)
        self.assertFalse(self.runtime.exists())

    def test_estado_corrupto_no_borra_interfaz(self):
        self.assertEqual(self.main(), 0)
        (self.runtime / "estado.json").write_text("{mal")
        self.assertEqual(self.main("leave"), 1)
        self.assertIsNotNone(self.sys.link)

    def test_ruta_conflictiva_se_rechaza(self):
        original = self.sys.__class__.__call__
        def execute(argv):
            if argv[:4] == ["ip", "-j", "route", "show"]:
                return '[{"dst":"10.90.0.0/24","dev":"eth0"}]'
            return original(self.sys, argv)
        from unittest.mock import patch
        with patch.object(Sistema, "__call__", lambda _, argv: execute(argv)):
            self.assertEqual(self.main(), 1)
        self.assertIsNone(self.sys.link)


if __name__ == "__main__":
    unittest.main()
