# Evidencia — modo live e inventario de licencias de la ISO de `v1.0.0` (2026-11-21)

ISO del release `v1.0.0`: commit `94f9b8f`,
`63eeb31a33c4a9d4a6597573a6f567d66b6afbbb207286ae7920197414cc0f10` (572 522 496 bytes). La copia
usada es idéntica byte a byte a la publicada en GitHub Releases (`cmp`, 21-nov).

## Modo live en QEMU (UEFI, 2048 MiB, sin interacción)

| Requisito | Herramienta | Resultado |
|---|---|---|
| RF-CORE-01 | `measure-ram-in-qemu.sh` (captura de la VGA) | Llega al escritorio Xfce |
| RNF-02 | `measure-ram-in-qemu.sh` (90 s en reposo) | **376 MiB** (MemTotal − MemAvailable), menos de 500 MB |
| RNF-01 | `verify-hermetismo-in-qemu.sh` (120 s en reposo, red SLIRP cautiva) | **0 sospechosos** (0 DNS, 0 NTP, 0 web, 0 SYN) de 12 paquetes; **0 listeners** de red |

Los 12 paquetes son de puesta en marcha local de la tarjeta. El único socket fuera de loopback es
el cliente DHCP (`udp/68`), que el criterio admite en el live. El sistema instalado no levanta la
red solo ([evidencia del 20-nov](2026-11-20-qemu-instalado-94f9b8f.md)).

Originales fuera de git, en `repro/out/medicion-live-v1.0.0-2026-11-21/`:

- `hermetismo.pcap`, SHA-256 `952ba6e430f5eeb3…`
- `ram-idle.log`, SHA-256 `36c8b3dc9d88ea41…`

## Inventario de licencias (RNF-04, HT-04 CA-1)

Leído del `var/lib/dpkg/status` y del pool APT **dentro del squashfs de la ISO**, con el contenedor
bookworm anclado (`debian@sha256:88200866…`). Lista completa:
[`paquetes-y-seccion.tsv`](2026-11-21-live-y-licencias-v1.0.0/paquetes-y-seccion.tsv).

| | Paquetes | En `main` | En `contrib` / `non-free` / `non-free-firmware` |
|---|---|---|---|
| Instalados en la ISO | **557** | 557 | **0** |
| Pool APT local | **38** | 38 | **0** |

- El componente `main` de Debian solo admite software libre según las
  [Directrices de Software Libre de Debian](https://www.debian.org/social_contract#guidelines).
- Los cinco paquetes propios (`nimbo-*`) son **GPL-3.0-or-later**.

## Límites

- El criterio de licencia es el componente de Debian. No se auditó a mano el fichero `copyright` de
  cada paquete.
- El costo cero de la infraestructura (HT-04 CA-2) no se puede leer desde el repo: el repositorio
  es público y usa GitHub Actions y Pages, pero la ausencia de cargos la confirma Juan José.
- QEMU, no hardware real.
