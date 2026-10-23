# Evidencia — ISO bit-idéntica entre máquinas físicas distintas (2026-10-23)

Prueba empírica del cierre de [H-001](../../docs/hallazgos/H-001-filtracion-nlink-btrfs.md)
con el arreglo de [ADR-007](../../docs/adr/ADR-007-initrd-sobre-tmpfs.md).

## Qué se compiló

- **Código:** commit `a4af6b8` (main tras el PR #24) + hook `9990-nimbo-initrd-tmpfs` y aviso
  de sistema de archivos (rama `fix/repro-initrd-tmpfs`).
- **`SOURCE_DATE_EPOCH` forzado a `1791342616`** (el de `a4af6b8`), para que la ÚNICA diferencia
  con la ISO de CI sea el arreglo. Si el hook dejara cualquier rastro en la imagen (punto de
  montaje, mtime, marcador), el SHA-256 no podría coincidir.

## Anfitrión

| | |
|---|---|
| Máquina | PC físico, Intel Core i7-1355U (13.ª gen.) |
| Sistema operativo | Omarchy (Arch Linux) |
| Kernel | Linux 7.2.5-3-omarchy x86_64 |
| Motor de contenedores | docker 29.7.2 |
| Sistema de archivos del build | **btrfs** |
| Imagen del contenedor | `debian@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171` |
| Snapshot | `20260901T000000Z` |
| Build | 2026-10-23 09:04:35 → 09:23:06 -05:00, `rc=0` |

## Comando

```
cd iso/live-build
SOURCE_DATE_EPOCH=1791342616 CONTAINER_ENGINE=docker ./build-in-container.sh
sha256sum live-image-amd64.hybrid.iso
cmp live-image-amd64.hybrid.iso <ISO de CI, run 37565498007 intento 2>
```

## Salida

```
P: [hook] initrd sobre tmpfs (ADR-007): montando tmpfs en /var/tmp
update-initramfs: Generating /boot/initrd.img-6.1.0-52-amd64
P: [hook]   /boot/initrd.img-6.1.0-52-amd64: 0 directorios con nlink=1 (OK)
P: [hook] initrd generado sobre tmpfs; chroot_hacks no lo regenerará
P: Begin executing hacks...
...
17ee64c8624d15416c4996e82585b235e187cc045313176f19cc0b8e049f1da0  live-image-amd64.hybrid.iso
cmp: IDÉNTICAS byte a byte
```

## Referencia de CI (mismo commit, ext4)

| Ejecución | SHA-256 |
|---|---|
| `build-iso` run `37565498007` intento 1 (2026-10-07) | `17ee64c8…1da0` |
| `repro-verify` run `37565498016` pata A (2026-10-07) | `17ee64c8…1da0` |
| `repro-verify` run `37565498016` pata B (2026-10-07) | `17ee64c8…1da0` |
| `build-iso` run `37565498007` intento 2 (2026-10-23) | `17ee64c8…1da0` |
| **Este PC (btrfs), con el arreglo** | **`17ee64c8…1da0`** |
| Este PC (btrfs), sin el arreglo | `41d97860…333a9d` ← H-001 |

ISO: 475 004 928 bytes.
