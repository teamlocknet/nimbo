# nimbo

Sistema operativo de ciberseguridad basado en Debian — proyecto de grado del grupo
**LockNet**. _Codename interno: `nimbo`, provisional_ (ver
[ADR-000](docs/adr/ADR-000-codename-y-nombre.md)).

## Organización del repositorio

- `docs/` — documentación: ADRs, documento maestro y manuales.
- `iso/` — construcción de la imagen: `live-build`, `xfce4`, `calamares`.
- `packages/` — paquetes propios: `nimbo-audit`, `nimbo-net`.
- `security/` — `luks-tpm`, `air-gapped`, `hardening`.
- `repro/` — compilaciones reproducibles.
- `apt-repo/` — repositorio APT de distribución.
- `ci/` — utilidades de integración continua.
- `.github/` — `CODEOWNERS` y workflows.

## Modelo de trabajo

El chat orquesta y diseña; Claude Code escribe el código real. El equipo humano
ejecuta las gestiones del mundo físico y **verifica con los ojos** antes de mergear.

## Referencias

- Fuente de verdad: [`docs/documento-maestro/`](docs/documento-maestro/)
- Decisiones de arquitectura: [`docs/adr/`](docs/adr/)

**Estado:** Fase 1 — cimientos.
