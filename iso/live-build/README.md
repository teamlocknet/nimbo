# iso/live-build

Configuración de **live-build** para construir la ISO **live mínima** de nimbo (Core OS).
Este es el **Paso 1A**: probar que live-build produce una ISO que **arranca a consola/login**,
verificándola en QEMU — *antes* de meterla en CI (1B) y *antes* de perseguir reproducibilidad
bit a bit (1C).

**Dueño:** Juan José

> Alcance de este ladrillo: **solo arranque a login**. SIN entorno de escritorio (Xfce4),
> hardening, Calamares, LUKS/TPM ni paquetes propios — eso son pasos posteriores. Aquí
> reducimos variables a propósito.

---

## Requisitos del host

Probado en **Fedora 44**. Necesitas: `podman`, `qemu-system-x86_64`, `socat` y `convert`
(ImageMagick). `/dev/kvm` es opcional (acelera QEMU).

> **La toolchain de Debian (live-build/debootstrap) NO se instala en el host.** Corre dentro
> de un contenedor `debian:bookworm-slim`, aislada de Fedora. Es 100% FOSS y deja la base
> anclable por digest para reproducibilidad futura.

## Cómo construir la ISO

```bash
sudo ./build-in-container.sh
```

- **Debe ser rootful (`sudo`)**: `debootstrap` crea *device nodes* (`mknod`), imposible en
  podman rootless (falla con `Operation not permitted`). El script no invoca `sudo` por su
  cuenta; lo antepones tú.
- Usa `--network=host` porque el podman rootful de Fedora no resuelve DNS con su backend
  propio (si no, `apt` no alcanza los mirrors de Debian).
- Fija `SOURCE_DATE_EPOCH` al timestamp del commit HEAD (determinista y trazable).
- Tarda ~10–20 min (debootstrap + squashfs + ISO).

### Motor de contenedor (paridad dev/CI)

El script es **agnóstico del motor** vía `CONTAINER_ENGINE` (por defecto `podman`):

```bash
sudo ./build-in-container.sh                    # local (Fedora): podman rootful
CONTAINER_ENGINE=docker ./build-in-container.sh # CI (ubuntu): docker --privileged
```

La CI (`.github/workflows/build-iso.yml`, Paso 1B) reutiliza **este mismo script** con
`CONTAINER_ENGINE=docker`, así local y la nube corren **exactamente la misma lógica de
build** (no se reinventa la receta). El `:Z` de SELinux y el `-t` de tty se aplican solo
cuando corresponde (podman/terminal); todo lo demás es idéntico.

**Salida:** `live-image-amd64.hybrid.iso` en esta carpeta.
**Tamaño obtenido:** **260 MB** (272 629 760 bytes) · live-build `20230502` · kernel
`6.1.0-52-amd64` (Debian 12 bookworm).

Los artefactos de build (`chroot/`, `binary/`, `cache/`, `config/`, `*.iso`, logs) están en
`.gitignore`; quedan propiedad de `root` (build rootful) — límpialos con
`sudo rm -rf chroot binary cache config .build local *.iso *.buildlog` si hace falta.

## Cómo probarla en QEMU (headless)

```bash
./test-in-qemu.sh                 # usa live-image-amd64.hybrid.iso por defecto
```

Arranca la ISO sin display, envía `Enter` al menú de isolinux por el monitor de QEMU y
espera el prompt de login. Evidencia:

- **`boot-serial.log`** — traza completa de arranque por consola serie (`console=ttyS0`),
  hasta `nimbo-live login:`. Es la evidencia principal (texto verificable).
- La captura VGA (`screendump`) sale **en negro** porque enrutamos la consola a serie; por
  eso el serial es la evidencia buena, no la imagen.

Verificado (Paso 1A): arranca hasta `serial-getty@ttyS0` → **`nimbo-live login:`**, con la
línea de kernel `boot=live components hostname=nimbo-live username=nimbo console=tty0
console=ttyS0,115200`.

---

## Reproducibilidad — estado y deuda conocida

Este paso aplica **higiene** de reproducibilidad, pero **NO persigue bit-idéntico todavía**
(eso es el Paso 1C con `diffoscope` y una segunda compilación comparada).

**Ya aplicado:**
- `SOURCE_DATE_EPOCH` = timestamp del commit HEAD (afecta timestamps de muchos artefactos).
  En CI se pasa explícito; el script lo respeta si viene del entorno.
- Entorno de build determinista: `TZ=UTC`, `LC_ALL=C.UTF-8`.
- Sin `apt-recommends` ni `apt-indices`: menos superficie y menos ruido.
- **Imagen base anclada por digest** del índice multi-arch
  (`debian:bookworm-slim@sha256:88200866…4171`), no por tag móvil. Así docker (CI) y podman
  (local) parten del mismo bit de base. Sobreescribible con `NIMBO_BASE_IMAGE=`.
- **Compresión del squashfs determinista** (`mksquashfs -processors 1`, vía
  `MKSQUASHFS_OPTIONS` en `auto/build`). La compresión xz multihilo no es determinista;
  single-thread la hace reproducible a cambio de más tiempo de build. Ver
  [ADR-001](../../docs/adr/ADR-001-compresion-determinista-squashfs.md).
- **Orden de empaquetado del squashfs determinista** (`-sort` con un sortfile completo).
  mksquashfs empaqueta los datos en orden de scan (`readdir`), no determinista entre dos
  `debootstrap`. `auto/build` genera en build-time `config/rootfs/squashfs.sort` con todos
  los ficheros del rootfs en orden `LC_ALL=C`, y live-build lo pasa a mksquashfs
  (`-sort squashfs.sort`) de forma nativa. Ver
  [ADR-002](../../docs/adr/ADR-002-orden-determinista-empaquetado-squashfs.md).
- **Caché binario de APT desactivado** (`Dir::Cache::pkgcache/srcpkgcache ""` en
  `apt.conf.d`). APT reserializa `/var/cache/apt/*.bin` en cada invocación con contenido no
  determinista (no lo cubre `SOURCE_DATE_EPOCH`); `auto/build` lo desactiva tras `lb chroot`
  para que no se escriba en ninguna etapa. Ver
  [ADR-003](../../docs/adr/ADR-003-cache-apt-determinista-squashfs.md).

**Fuentes de no-determinismo aún abiertas (a cerrar en 1C):**
1. **Versiones de paquetes**: los mirrors por defecto (`deb.debian.org`) son *rolling*; dos
   builds en fechas distintas pueden traer versiones distintas. → **Decisión anotada:** anclar
   a **`snapshot.debian.org`** (mirror con fecha fija) vía `--mirror-*` en `auto/config`. NO
   implementado aquí para no arriesgar el primer arranque; es el siguiente paso de repro.
2. **Metadatos de compresión** (gzip/xz: nivel, timestamps embebidos) del initrd.
3. **`SOURCE_DATE_EPOCH`** no cubre todo (algunos generadores ignoran la variable) — se
   documentarán los residuos con `diffoscope`.

## Decisiones abiertas

- **Distro fijada a Debian 12 (bookworm)** para este ladrillo, por ser la base más probada
  con live-build. **"Qué Debian Stable se envía finalmente" queda PENDIENTE** (candidato:
  trixie/Debian 13). El cambio es un **one-liner** en `auto/config` (`--distribution`). Se
  registrará en un ADR cuando se decida.

## Lo que NO está en este paso (anti-desborde)

Sin workflow de CI que compile la ISO (Paso 1B), sin `diffoscope` ni build comparado
(Paso 1C), sin Xfce4/hardening/Calamares/LUKS/TPM, sin paquetes ni CLI.
