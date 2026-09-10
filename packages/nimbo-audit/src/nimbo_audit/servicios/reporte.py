"""Render del reporte consolidado en Markdown (RF-04 / CU-03).

Función PURA y determinista: recibe el estado ya recopilado (engagement +
evidencias verificadas + registros de sesión) y devuelve el texto Markdown. No
toca el FS ni el reloj de pared: dado un engagement fijo, el `.md` es estable
(mismo contenido -> mismo texto), coherente con el principio de reproducibilidad.

Aislar el render del IO permite testear el contenido sin disco y mantener a
`ComandoReport` como mero orquestador (repos + hashing + este render).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from nimbo_audit.modelos.engagement import Engagement

if TYPE_CHECKING:  # evita import circular en runtime
    from nimbo_audit.comandos.report import EvidenciaVerificada


def renderizar_reporte(
    engagement: Engagement,
    evidencias: Sequence["EvidenciaVerificada"],
    sesion: Sequence[str],
) -> str:
    """Construye el reporte Markdown de un engagement.

    - `evidencias`: registros del índice, ya verificados (estado de integridad
      recomputado contra el hash ancla).
    - `sesion`: nombres de los registros de sesión presentes en `logs/`
      (RF-02 aún no genera este log; su ausencia se tolera con gracia).
    """
    lineas: list[str] = []
    lineas.append(f"# Reporte de auditoría — {engagement.id}")
    lineas.append("")

    # --- 1. Datos del engagement --------------------------------------------
    lineas.append("## 1. Datos del engagement")
    lineas.append("")
    lineas.append(f"- **Identificador:** {engagement.id}")
    lineas.append(f"- **Fecha de inicio:** {engagement.fecha_inicio}")
    lineas.append(f"- **Analista:** {engagement.analista}")
    lineas.append("")

    # --- 2. Cronología de la sesión -----------------------------------------
    lineas.append("## 2. Cronología de la sesión")
    lineas.append("")
    if sesion:
        for registro in sorted(sesion):
            lineas.append(f"- `logs/{registro}`")
    else:
        lineas.append("No hay registro de sesión (RF-02 pendiente).")
    lineas.append("")

    # --- 3. Evidencia registrada --------------------------------------------
    lineas.append(f"## 3. Evidencia registrada ({len(evidencias)} archivos)")
    lineas.append("")
    if evidencias:
        lineas.append("| # | Nombre | Ruta | SHA-256 | Registrado (UTC) | Integridad |")
        lineas.append("|---|--------|------|---------|------------------|------------|")
        for i, ev in enumerate(evidencias, start=1):
            e = ev.evidencia
            lineas.append(
                f"| {i} | {e.nombre} | {e.ruta} | `{e.sha256}` "
                f"| {e.timestamp} | {ev.estado} |"
            )
    else:
        lineas.append("No hay evidencia registrada en este engagement.")
    lineas.append("")

    # --- Resumen de integridad ----------------------------------------------
    resumen = _contar_estados(evidencias)
    lineas.append(
        "**Resumen de integridad:** "
        f"{resumen['OK']} OK · {resumen['MODIFICADO']} MODIFICADO · "
        f"{resumen['AUSENTE']} AUSENTE"
    )
    lineas.append("")

    return "\n".join(lineas)


def _contar_estados(
    evidencias: Sequence["EvidenciaVerificada"],
) -> dict[str, int]:
    resumen = {"OK": 0, "MODIFICADO": 0, "AUSENTE": 0}
    for ev in evidencias:
        resumen[ev.estado] += 1
    return resumen
