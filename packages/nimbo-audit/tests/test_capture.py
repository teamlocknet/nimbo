"""Tests de `nimbo-audit capture` (RF-03 / CU-02).

Rápidos y herméticos: usan tmp_path, nunca el home real. Cubren el flujo OK
(copia + SHA-256 + index.json bien formado), archivo-no-encontrado (CU-02 3a),
el rechazo de duplicados (integridad: nada se sobrescribe en silencio), la
detección de modificación por comparación de hash y — punto crítico — la
degradación graciosa ante restricción de memoria (RNF-08 / CU-02 4a): [AVISO]
limpio, estado intacto y sin traceback.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nimbo_audit.cli import app
from nimbo_audit.comandos.capture import ComandoCapture, resolver_engagement_activo
from nimbo_audit.comandos.init import ComandoInit
from nimbo_audit.errores import (
    ArchivoNoAccesibleError,
    EngagementNoActivoError,
    EvidenciaDuplicadaError,
    InterrupcionMemoriaError,
)
from nimbo_audit.repositorio.engagement_repo import RepositorioEngagementJSON
from nimbo_audit.repositorio.evidencia_repo import RepositorioEvidenciaJSON
from nimbo_audit.servicios.hashing import calcular_sha256

FECHA_FIJA = datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc)


def _engagement(base: Path, nombre: str = "acme") -> Path:
    """Crea un engagement real (vía init) y devuelve su raíz."""
    return ComandoInit(
        nombre, RepositorioEngagementJSON(base), analista="tester", ahora=FECHA_FIJA
    ).ejecutar()


def _archivo(tmp_path: Path, nombre: str, contenido: bytes) -> Path:
    p = tmp_path / nombre
    p.write_bytes(contenido)
    return p


def _capturar(root: Path, origen: Path, **kw):
    return ComandoCapture(
        origen, RepositorioEvidenciaJSON(root), ahora=FECHA_FIJA, **kw
    ).ejecutar()


# --- Servicio de hashing: streaming == hashlib -------------------------------


def test_hashing_streaming_coincide_con_hashlib(tmp_path: Path) -> None:
    contenido = b"nimbo" * 100_000  # varios chunks
    origen = _archivo(tmp_path, "grande.bin", contenido)
    # chunk pequeño fuerza múltiples lecturas: el resultado no debe depender de él.
    assert calcular_sha256(origen, chunk_size=64) == hashlib.sha256(contenido).hexdigest()


# --- Flujo principal (CU-02) -------------------------------------------------


def test_capture_ok_copia_hash_e_index(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    contenido = b"paquete capturado"
    origen = _archivo(tmp_path, "captura.pcap", contenido)

    ev = _capturar(root, origen)

    # Copia física en evidencia/.
    copia = root / "evidencia" / "captura.pcap"
    assert copia.read_bytes() == contenido
    # Hash correcto.
    assert ev.sha256 == hashlib.sha256(contenido).hexdigest()

    # index.json bien formado.
    index = json.loads((root / "evidencia" / "index.json").read_text(encoding="utf-8"))
    assert index["version"] == 1
    assert index["evidencias"] == [
        {
            "nombre": "captura.pcap",
            "ruta": "evidencia/captura.pcap",
            "sha256": ev.sha256,
            "timestamp": "2026-09-09T12:00:00+00:00",
        }
    ]


def test_index_determinista_ordenado_y_con_newline(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    _capturar(root, _archivo(tmp_path, "a.txt", b"A"))
    _capturar(root, _archivo(tmp_path, "b.txt", b"B"))

    texto = (root / "evidencia" / "index.json").read_text(encoding="utf-8")
    assert texto.endswith("\n")
    # claves ordenadas dentro de cada objeto
    assert '"nombre"' in texto and texto.index('"nombre"') < texto.index('"ruta"')
    # orden cronológico (cadena de evidencia): a antes que b
    index = json.loads(texto)
    assert [e["nombre"] for e in index["evidencias"]] == ["a.txt", "b.txt"]


# --- CU-02 3a: archivo no encontrado ----------------------------------------


def test_archivo_no_encontrado_no_toca_index(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    with pytest.raises(ArchivoNoAccesibleError):
        _capturar(root, tmp_path / "no-existe.pcap")
    # index.json no se creó; evidencia/ sigue vacía.
    assert not (root / "evidencia" / "index.json").exists()
    assert list((root / "evidencia").iterdir()) == []


# --- Integridad: nada se sobrescribe en silencio -----------------------------


def test_duplicado_rechazado_estado_intacto(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    origen = _archivo(tmp_path, "captura.pcap", b"original")
    _capturar(root, origen)

    otro = _archivo(tmp_path, "captura.pcap", b"otro contenido")  # mismo nombre
    with pytest.raises(EvidenciaDuplicadaError):
        _capturar(root, otro)

    # La copia y el índice originales quedan intactos (sin sobrescritura silenciosa).
    assert (root / "evidencia" / "captura.pcap").read_bytes() == b"original"
    index = json.loads((root / "evidencia" / "index.json").read_text(encoding="utf-8"))
    assert len(index["evidencias"]) == 1


def test_modificacion_posterior_es_detectable(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    origen = _archivo(tmp_path, "captura.pcap", b"original")
    ev = _capturar(root, origen)

    # Alguien manipula la evidencia ya registrada.
    copia = root / "evidencia" / "captura.pcap"
    copia.write_bytes(b"MANIPULADO")

    # El hash almacenado es el ancla: recomputar lo delata.
    assert calcular_sha256(copia) != ev.sha256


# --- RNF-08 / CU-02 4a: degradación graciosa (restricción de memoria) --------


def _hasher_oom(_ruta: Path, *, chunk_size: int = 0) -> str:
    raise MemoryError("simulando OOM Killer / MemoryError")


def test_memoryerror_avisa_limpio_y_no_corrompe(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    origen = _archivo(tmp_path, "enorme.bin", b"contenido")

    with pytest.raises(InterrupcionMemoriaError):
        _capturar(root, origen, hasher=_hasher_oom)

    # El archivo NO fue registrado y el estado del engagement queda intacto.
    assert not (root / "evidencia" / "captura.pcap").exists()
    assert not (root / "evidencia" / "enorme.bin").exists()
    assert not (root / "evidencia" / "index.json").exists()
    assert (root / "metadata.json").is_file()  # metadata previa sin tocar


# --- Resolución del engagement activo ---------------------------------------


def test_resolver_autodetect_subiendo_desde_cwd(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    subdir = root / "evidencia"
    assert resolver_engagement_activo(subdir, None) == root.resolve()


def test_resolver_override_directo(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    assert resolver_engagement_activo(tmp_path, root) == root.resolve()


def test_resolver_sin_engagement_falla(tmp_path: Path) -> None:
    vacio = tmp_path / "sin_engagement"
    vacio.mkdir()
    with pytest.raises(EngagementNoActivoError):
        resolver_engagement_activo(vacio, None)
    with pytest.raises(EngagementNoActivoError):
        resolver_engagement_activo(tmp_path, vacio)  # override sin metadata.json


# --- CLI: mensajes exactos [OK] / [ERROR] / [AVISO] --------------------------


def test_cli_capture_ok(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    origen = _archivo(tmp_path, "captura.pcap", b"datos")
    res = CliRunner().invoke(app, ["capture", str(origen), "--dir", str(root)])
    assert res.exit_code == 0
    assert "[OK] Evidencia registrada:" in res.stdout
    assert "SHA-256:" in res.stdout
    assert (root / "evidencia" / "captura.pcap").is_file()


def test_cli_archivo_no_encontrado(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    res = CliRunner().invoke(
        app, ["capture", str(tmp_path / "no-existe"), "--dir", str(root)]
    )
    assert res.exit_code == 1
    assert (
        "[ERROR] No se pudo acceder al archivo especificado. Verifique la ruta."
        in res.stderr
    )


def test_cli_sin_engagement_activo(tmp_path: Path) -> None:
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    origen = _archivo(tmp_path, "captura.pcap", b"datos")
    res = CliRunner().invoke(app, ["capture", str(origen), "--dir", str(vacio)])
    assert res.exit_code == 1
    assert "[ERROR]" in res.stderr
