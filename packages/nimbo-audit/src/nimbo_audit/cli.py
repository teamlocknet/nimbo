"""Punto de entrada del CLI (app Typer). Cablea los subcomandos y traduce las
excepciones propias a mensajes limpios `[OK]` / `[ERROR]` (sin traceback crudo).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from nimbo_audit.comandos.capture import ComandoCapture, resolver_engagement_activo
from nimbo_audit.comandos.init import ComandoInit
from nimbo_audit.errores import (
    ArchivoNoAccesibleError,
    EngagementExistenteError,
    EngagementNoActivoError,
    EvidenciaDuplicadaError,
    InterrupcionMemoriaError,
    NimboAuditError,
    NombreInvalidoError,
)
from nimbo_audit.repositorio.engagement_repo import RepositorioEngagementJSON
from nimbo_audit.repositorio.evidencia_repo import RepositorioEvidenciaJSON

app = typer.Typer(
    help="CLI de auditoría (codename nimbo): inicializa y gestiona engagements.",
    add_completion=False,
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """Fuerza modo multi-comando: el nombre del subcomando (`init`, y luego
    `capture`/`report`) se conserva aunque hoy exista uno solo."""


def _base_por_defecto() -> Path:
    """Ubicación por defecto de los engagements: <home del usuario>/audits."""
    return Path.home() / "audits"


@app.command(help="Inicializa un engagement de auditoría (RF-01 / CU-01).")
def init(
    cliente: str = typer.Argument(..., help="Nombre/identificador del engagement."),
    force: bool = typer.Option(
        False,
        "--force",
        help="Reinicializa aunque exista (ADVERTENCIA: puede borrar evidencia previa).",
    ),
    dir: Optional[Path] = typer.Option(
        None,
        "--dir",
        "-d",
        help="Directorio base de engagements (por defecto ~/audits).",
    ),
) -> None:
    base = dir if dir is not None else _base_por_defecto()
    repo = RepositorioEngagementJSON(base)
    comando = ComandoInit(cliente, repo, force=force)

    try:
        ruta = comando.ejecutar()
    except EngagementExistenteError:
        typer.echo("[ERROR] Ya existe un engagement con este nombre", err=True)
        typer.echo(
            f"        Sugerencia: usa otro identificador (p. ej. '{cliente}-2') "
            "o --force para reinicializar (ADVERTENCIA: --force puede borrar "
            "evidencia previa).",
            err=True,
        )
        raise typer.Exit(code=1)
    except NombreInvalidoError:
        typer.echo(
            f"[ERROR] Nombre no válido: '{cliente}'. Usa solo letras, dígitos, "
            "'.', '-' y '_' (sin barras ni '..').",
            err=True,
        )
        raise typer.Exit(code=1)
    except NimboAuditError as exc:  # red de seguridad: nunca traceback crudo
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"[OK] Engagement '{cliente}' inicializado en {ruta}")


@app.command(help="Registra un archivo como evidencia con integridad SHA-256 (RF-03 / CU-02).")
def capture(
    archivo: Path = typer.Argument(..., help="Archivo a registrar como evidencia."),
    dir: Optional[Path] = typer.Option(
        None,
        "--dir",
        "-d",
        help="Raíz del engagement (por defecto se detecta subiendo desde el directorio actual).",
    ),
) -> None:
    try:
        raiz = resolver_engagement_activo(Path.cwd(), dir)
    except EngagementNoActivoError:
        typer.echo(
            "[ERROR] No hay un engagement activo. Ubícate dentro de un engagement "
            "o indícalo con --dir <ruta>.",
            err=True,
        )
        raise typer.Exit(code=1)

    repo = RepositorioEvidenciaJSON(raiz)
    comando = ComandoCapture(archivo, repo)

    try:
        evidencia = comando.ejecutar()
    except ArchivoNoAccesibleError:
        typer.echo(
            "[ERROR] No se pudo acceder al archivo especificado. Verifique la ruta.",
            err=True,
        )
        raise typer.Exit(code=1)
    except EvidenciaDuplicadaError:
        typer.echo(
            f"[ERROR] Ya existe evidencia registrada con el nombre '{archivo.name}'. "
            "No se sobrescribe evidencia en silencio.",
            err=True,
        )
        raise typer.Exit(code=1)
    except InterrupcionMemoriaError:
        typer.echo(
            "[AVISO] La operación fue interrumpida por restricción de memoria. "
            "El archivo no fue registrado; el engagement queda intacto.",
            err=True,
        )
        raise typer.Exit(code=1)
    except NimboAuditError as exc:  # red de seguridad: nunca traceback crudo
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(
        f"[OK] Evidencia registrada: {archivo} (SHA-256: {evidencia.sha256})"
    )


def main() -> None:
    """Entrypoint de consola (`nimbo-audit`)."""
    app()


if __name__ == "__main__":
    main()
