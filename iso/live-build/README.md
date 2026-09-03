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
- Entorno de build determinista: `TZ=UTC`, `LC_ALL=C.UTF-8`.
- Sin `apt-recommends` ni `apt-indices`: menos superficie y menos ruido.

**Fuentes de no-determinismo aún abiertas (a cerrar en 1C):**
1. **Versiones de paquetes**: los mirrors por defecto (`deb.debian.org`) son *rolling*; dos
   builds en fechas distintas pueden traer versiones distintas. → **Decisión anotada:** anclar
   a **`snapshot.debian.org`** (mirror con fecha fija) vía `--mirror-*` en `auto/config`. NO
   implementado aquí para no arriesgar el primer arranque; es el siguiente paso de repro.
2. **Imagen base del contenedor**: hoy tag `debian:bookworm-slim` (móvil). → Anclar por
   **digest** (`debian@sha256:…`) con `NIMBO_BASE_IMAGE=`. Trivial y sin riesgo de arranque;
   se hará al entrar a repro.
3. **Orden de archivos y metadatos en squashfs** (mtimes, orden de inodos).
4. **Metadatos de compresión** (gzip/xz: nivel, timestamps embebidos) del squashfs y del
   initrd.
5. **`SOURCE_DATE_EPOCH`** no cubre todo (algunos generadores ignoran la variable) — se
   documentarán los residuos con `diffoscope`.

## Decisiones abiertas

- **Distro fijada a Debian 12 (bookworm)** para este ladrillo, por ser la base más probada
  con live-build. **"Qué Debian Stable se envía finalmente" queda PENDIENTE** (candidato:
  trixie/Debian 13). El cambio es un **one-liner** en `auto/config` (`--distribution`). Se
  registrará en un ADR cuando se decida.

## Lo que NO está en este paso (anti-desborde)

Sin workflow de CI que compile la ISO (Paso 1B), sin `diffoscope` ni build comparado
(Paso 1C), sin Xfce4/hardening/Calamares/LUKS/TPM, sin paquetes ni CLI.
