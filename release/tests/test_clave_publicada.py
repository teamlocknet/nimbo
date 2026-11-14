import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
CLAVE = ROOT / "nimbo-release-publica.asc"
# Canales independientes de ADR-015 (README raíz y sustentación) y la copia de release/.
# En el contenedor de CI solo se monta release/: los canales de fuera no existen allí.
CANALES = [ROOT / "README.md", REPO / "README.md", REPO / "docs" / "sustentacion" / "README.md"]
HUELLA = re.compile(r"Huella primaria:\s*`([0-9A-F ]+)`")


def huella_publicada(path):
    found = HUELLA.findall(path.read_text(encoding="utf-8"))
    if len(found) != 1:
        raise AssertionError(f"{path}: se espera una sola 'Huella primaria', hay {len(found)}")
    return found[0].replace(" ", "")


class ClavePublicada(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("release_tool", ROOT / "release.py")
        cls.tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.tool)

    def test_canales_publican_la_misma_huella(self):
        fuera = [p for p in CANALES[1:] if not p.is_file()]
        if fuera:
            self.skipTest(f"sin el repositorio completo (falta {fuera[0].relative_to(REPO)})")
        huellas = {str(p.relative_to(REPO)): huella_publicada(p) for p in CANALES}
        self.assertEqual(len(set(huellas.values())), 1, huellas)

    def test_clave_versionada_corresponde_a_la_huella(self):
        expected = self.tool.fingerprint(huella_publicada(CANALES[0]))
        with tempfile.TemporaryDirectory(prefix="nimbo-clave-publicada-") as tmp:
            home = Path(tmp)
            home.chmod(0o700)
            # keyring() rechaza material secreto, UID distinta de una y otra primaria.
            ring = self.tool.keyring(home, CLAVE, expected)
            self.assertGreater(ring.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
