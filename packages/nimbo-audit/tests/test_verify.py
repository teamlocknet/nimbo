"""RF-AUD-04 / HU-13: verificacion independiente del caso."""
from pathlib import Path

from nimbo_audit.cli import app
from nimbo_audit.comandos.init import ComandoInit
from nimbo_audit.comandos.capture import ComandoCapture
from nimbo_audit.repositorio.engagement_repo import RepositorioEngagementJSON
from nimbo_audit.repositorio.evidencia_repo import RepositorioEvidenciaJSON


def test_verify_caso_integro(tmp_path: Path, cli_runner) -> None:
    raiz = ComandoInit("acme", RepositorioEngagementJSON(tmp_path)).ejecutar()
    origen = tmp_path / "captura.txt"
    origen.write_bytes(b"evidencia intacta")
    ComandoCapture(origen, RepositorioEvidenciaJSON(raiz)).ejecutar()

    resultado = cli_runner.invoke(app, ["verify", str(raiz)])

    assert resultado.exit_code == 0, resultado.output
    assert "captura.txt" in resultado.stdout
    assert "OK" in resultado.stdout
