# nimbo

Sistema operativo de ciberseguridad basado en Debian — proyecto de grado del grupo
**LockNet**. _Codename interno: `nimbo`, provisional_ (ver
[ADR-000](docs/adr/ADR-000-codename-y-nombre.md)).

## Organización del repositorio

- `docs/` — documentación: ADRs, documento maestro y manuales.
- `iso/` — construcción de la imagen: `live-build`, `xfce4`, `calamares`.
- `packages/` — paquetes propios: `nimbo-audit`, `nimbo-nav`, `nimbo-net`, `nimbo-red`,
  `nimbo-update-offline`.
- `security/` — `luks-tpm`, `air-gapped`, `hardening`.
- `repro/` — compilaciones reproducibles.
- `apt-repo/` — repositorio APT de distribución.
- `release/` — release firmado y procedencia.
- `ci/` — utilidades de integración continua.
- `.github/` — `CODEOWNERS` y workflows.

## Modelo de trabajo

El chat orquesta y diseña; Claude Code escribe el código real. El equipo humano
ejecuta las gestiones del mundo físico y **verifica con los ojos** antes de mergear.

## Verificar un release

Los releases se firman con una subclave de la clave de release de LockNet
([ADR-015](docs/adr/ADR-015-custodia-y-release-firmado.md)). Este README es uno de los dos
canales independientes de la huella; el otro es el
[material de sustentación](docs/sustentacion/README.md). La `release-key.asc` que viaja junto a
la ISO **no basta por sí sola**: su huella tiene que coincidir con esta.

- Huella primaria: `0C50 B739 1A9B 8CFF 8A36  A627 D3B9 111F EC57 48C6`
- Clave pública: [`release/nimbo-release-publica.asc`](release/nimbo-release-publica.asc)
  (primaria ed25519 solo para certificar, caduca el 2028-11-12; subclave de firma ed25519,
  caduca el 2027-11-13).
- Cómo verificar: [`release/README.md`](release/README.md).

## Licencia

El código propio de este repositorio se distribuye bajo **GPL-3.0-or-later**: texto
completo en [`LICENSE`](LICENSE). La ISO agrega además paquetes de Debian, cada uno con
su propia licencia (ver `/usr/share/doc/*/copyright` dentro del sistema).
Procedencia de los recursos gráficos (branding del instalador): [`CREDITOS.md`](CREDITOS.md).

## Referencias

- Decisiones de arquitectura: [`docs/adr/`](docs/adr/)
- Guías de uso por módulo: [`docs/manuales/guias-de-uso.md`](docs/manuales/guias-de-uso.md)
- Documento maestro histórico (v2.0, desactualizado):
  [`docs/documento-maestro/`](docs/documento-maestro/)

## Estado (21-nov-2026)

[`v1.0.0`](https://github.com/teamlocknet/nimbo/releases/tag/v1.0.0) está publicado y firmado:
commit `94f9b8f`, ISO `63eeb31a…0f10`, con el mismo SHA-256 en dos compilaciones independientes
e instalada en QEMU con Secure Boot y LUKS
([evidencia](repro/evidencia/2026-11-20-qemu-instalado-94f9b8f.md)).

Pendiente:

- Verificación en hardware real con TPM (en QEMU ya pasó).
- Validación del repositorio APT `v1.0.0` en una VM limpia (RF-DIST-01). Ya está publicado y
  firmado.
- Validación con un Design Partner externo (RNF-06).
