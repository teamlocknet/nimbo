# iso/live-build

Configuración de **live-build** para construir la ISO **live** de nimbo (Core OS),
verificándola en QEMU. Historia por ladrillos: **1A** arranque a consola/login · **1B**
compilar en CI · **1C** reproducibilidad bit a bit · **3A** escritorio Xfce4 mínimo +
medición de RAM idle (ver sección abajo).

**Dueño:** Juan José

> Alcance acumulado hasta 3A: ISO que **arranca a un escritorio Xfce4 mínimo** (<500 MB RAM
> idle). Aún SIN hardening del escritorio (3B), Calamares, LUKS/TPM ni paquetes propios —
> eso son pasos posteriores. Seguimos reduciendo variables a propósito.

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
**Tamaño obtenido:** **260 MB** en 1A (sin escritorio) → **381 MB** en 3A (con Xfce4 mínimo,
ver sección Paso 3A) · live-build `20230502` · kernel `6.1.0-52-amd64` (Debian 12 bookworm).

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

## Paso 3A — Escritorio Xfce4 mínimo + RAM idle

El escritorio entra por una **lista de paquetes curada** (no un metapaquete): ver
`config/package-lists/desktop.list.chroot` y `iso/xfce4/README.md` para el qué y el porqué
de cada paquete. **Tamaño de la ISO con Xfce:** **381 MB** (vs 260 MB de la 1A).

**Login / autologin de la sesión live.** live-config crea el usuario `nimbo` (contraseña por
defecto `live`) **solo si `user-setup` está instalado**; como es "Recomienda" de live-config
y la receta usa `--apt-recommends false`, hay que declararlo explícito (junto con `sudo`) en
la lista de paquetes — si falta, *no se crea el usuario* y tanto el login como el autologin
fallan. El autologin al escritorio lo fija un drop-in propio
`config/includes.chroot/etc/lightdm/lightdm.conf.d/50-nimbo-autologin.conf` con la sección
`[Seat:*]` (live-config 11 escribe la obsoleta `[SeatDefaults]`, que lightdm 1.26 ignora).
El PAM `lightdm-autologin` de Debian permite a cualquier no-root, así que no hace falta el
grupo `autologin`. **Nota de seguridad (para 3B):** autologin + usuario con sudo + contraseña
por defecto es el estándar de un medio *live* efímero; el sistema instalado (Calamares +
LUKS/TPM) lleva credenciales reales.

> **Actualización 3B.1 (D14):** este drop-in horneado en `/etc/lightdm/` se **retiró** porque
> se filtraba también al sistema instalado. El autologin lo genera ahora **solo en el arranque
> live** el script live-config `config/includes.chroot/lib/live/config/0150-nimbo-autologin`
> (live-only por construcción). Ver la sección **Paso 3B.1** más abajo.

### Medir la RAM idle (`< 500 MB`, RNF-04 / Acta)

```bash
./measure-ram-in-qemu.sh          # usa live-image-amd64.hybrid.iso por defecto
```

Arnés **host-side y honesto**: NO hornea nada de medición en la ISO. Arranca la VM (VGA std,
2048 MiB, settle fijo 90 s), captura el escritorio por `screendump` (evidencia visual) y
entra por la consola serie (getty que ya existe por `console=ttyS0`) con `nimbo`/`live` para
leer `/proc/meminfo`. Fórmula idéntica a `free`: `used = MemTotal − MemAvailable` (huella
real en reposo, independiente del tamaño de la VM). Evidencia: `ram-desktop.png` (escritorio)
y `ram-idle.log` (números + veredicto). Reproducible: mismo settle, misma RAM de VM, misma
fórmula.

**Medición obtenida:** RAM idle **368 MiB** (`used = 2 014 152 − 1 637 208 kB`) →
**OK ✅ 368 MiB < 500 MB**. Escritorio Xfce4 arrancado por autologin, en reposo.

---

## Paso 3B.1 — Hardening del base: hermetismo + superficie + autologin live-only

Endurecimiento del **sistema base** por dos vías, **sin** sysctl fino de kernel/red ni
política de cuentas/PAM (eso es **3B.2**), sin Calamares/LUKS/TPM ni navegadores. Todo
verificado contra el **chroot real de 3A (398 paquetes)**, no contra supuestos.

### A) Hermetismo / telemetría off (RNF-01)

Mecanismo: **hook chroot de build-time** `config/hooks/normal/0100-nimbo-hermetismo.hook.chroot`
(determinista → no rompe la reproducibilidad; no descarga nada, no depende de red ni reloj).

- **La telemetría "clásica" NUNCA entró** — y documentarlo con evidencia vale más que fingir
  que la apagamos. Por `--apt-recommends false` desde 1A, **no están instalados**:
  `popularity-contest`, `reportbug`, `apport`/`whoopsie`, `systemd-timesyncd` (⇒ sin NTP
  saliente), `systemd-resolved` (⇒ sin DNS-fallback de vendor), `avahi-daemon`, `cups`,
  `exim4`/`postfix`, `openssh-server`, `NetworkManager`, `unattended-upgrades`. Además, los
  **únicos sockets habilitados** son `dbus`/`journald`/`udev` = **UNIX/netlink locales**:
  **cero listeners TCP/UDP** de fábrica.
- El **único canal de "phone home" en idle** que sí trae el base son los timers de apt:
  `apt-daily.timer` / `apt-daily-upgrade.timer` (→ `apt.systemd.daily update|install`, que
  llaman `apt-helper wait-online` y salen al mirror), más su **ruta gemela por cron**
  `/etc/cron.daily/apt-compat`. El hook **enmascara** ambos timers y sus `.service` (symlinks
  a `/dev/null`, deterministas) **y** escribe `/etc/apt/apt.conf.d/99nimbo-no-telemetry` con
  `APT::Periodic::Enable "0"` → cierra **ambas** vías (cinturón y tirantes).
- Coherente con **air-gapped (RF-CORE-06)**: las actualizaciones van por
  `nimbo-update-offline` + GPG, nunca auto-update silencioso. (El mask persiste al sistema
  instalado: **intencional y correcto**, no una fuga.)

### B) Reducción de superficie

El base 3A ya es **quirúrgico**: no hay paquetes-grasa que quitar sin arriesgar el
`debootstrap`, y no se quita por quitar. La única superficie que sobra y es **provablemente
segura** son los timers `apt-daily*` (arriba: superficie **y** red). **Se CONSERVAN** con
justificación: `cron.service`, `fstrim.timer`, `e2scrub_*` → locales, **sin red**, y
`fstrim`/`e2scrub` son **útiles en el sistema instalado**; su masking se hornearía al
squashfs, así que se **difiere al paso de Calamares**.

### Autologin live vs instalado (D14)

El autologin deja de ser un **fichero horneado** en `/etc/lightdm/…` (se filtraba al sistema
instalado vía squashfs). Ahora lo genera **en el arranque live** un **script live-config**
`config/includes.chroot/lib/live/config/0150-nimbo-autologin`: **live-only por construcción**
(live-config no corre en el sistema instalado por Calamares) ⇒ el autologin **nunca persiste
a instalado** (coherente **RNF-02**). Escribe la sección `[Seat:*]` correcta que 3A validó y
toma el usuario de `username=` del bootappend. Reproducibilidad intacta: es un fichero
estático en el squashfs; su efecto es en runtime, no altera los bytes de la ISO.

### Evidencia de hermetismo (`verify-hermetismo-in-qemu.sh`)

```bash
./verify-hermetismo-in-qemu.sh    # usa live-image-amd64.hybrid.iso por defecto
```

Arnés **host-side** (no hornea nada en la ISO): arranca la VM con **red cautiva** de QEMU
(user-mode SLIRP `10.0.2.0/24`, **no toca Internet**) y captura **cada paquete** del guest con
`-object filter-dump` → `hermetismo.pcap`. Tras una **ventana idle fija** (120 s) sin
interacción, lee por la consola serie los **sockets en escucha** del guest (`ss` + `/proc/net`
como verdad de base) y analiza el pcap con `tcpdump`. **Veredicto PASS** ⇔ **0 paquetes
sospechosos** (DNS/NTP/HTTP-S/SYN saliente) **y 0 listeners de red** no-loopback; solo se
admite la **puesta en marcha local** de la NIC (ARP/DHCP/NDP). Evidencia: `hermetismo.log`
(veredicto), `hermetismo.pcap` (traza) y `hermetismo-desktop.png` (escritorio usable).

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
- **`.disk/archive_trace` normalizado** (hook `config/hooks/normal/9000-archive-trace.hook.binary`).
  live-build rellena ese fichero descargando la traza del mirror (`project/trace/*`), que
  `snapshot.debian.org` devuelve **intermitente** (a veces un timestamp, a veces vacío) →
  rompía la reproducibilidad entre runners aunque el resto de la ISO fuera bit-idéntico
  (diagnosticado con `diffoscope`: era la ÚNICA diferencia). No lo cubre `SOURCE_DATE_EPOCH`.
  El hook lo fija a un valor determinista derivado de `NIMBO_SNAPSHOT`; corre en
  `binary_hooks`, así `SHA256SUM.TXT` y la ISO lo recogen. Era **latente desde 1A** (el
  `repro-verify` base pasaba por suerte); el Paso 3A lo destapó.

**Fuentes de no-determinismo aún abiertas (a cerrar en 1C):**
1. **Versiones de paquetes**: ~~los mirrors por defecto (`deb.debian.org`) son *rolling*~~
   **CERRADO (1C.5 + 1C.6, [ADR-004](../../docs/adr/ADR-004-anclaje-temporal-snapshot-debian-org.md)):**
   el **build** se ancla a `snapshot.debian.org` con un timestamp fijo y versionado en **una
   sola fuente de verdad** (`snapshot.env` → `NIMBO_SNAPSHOT`, sourceado por `auto/config` y
   `build-in-container.sh`). Quedan ancladas las **4 capas**: imagen base (digest, 1B) +
   **toolchain `live-build`** (snapshot, 1C.6) + paquetes del producto (snapshot, 1C.5) +
   receta determinista (ADR-001/002/003) → mismo commit ⇒ mismo hash a lo largo del tiempo.
   El **runtime** del producto se deja en `deb.debian.org` a propósito (doble estándar
   build/runtime, ver ADR-004). El `Valid-Until` del archivo de seguridad se maneja con
   `Acquire::Check-Valid-Until=false` **manteniendo la firma GPG** — práctica recomendada para
   snapshots, no un hack. (Toolchain vía http por ca-certs; producto vía https — ver ADR-004.)
2. **Metadatos de compresión** (gzip/xz: nivel, timestamps embebidos) del initrd.
3. **`SOURCE_DATE_EPOCH`** no cubre todo (algunos generadores ignoran la variable) — se
   documentarán los residuos con `diffoscope`.

## Decisiones abiertas

- **Distro fijada a Debian 12 (bookworm)** para este ladrillo, por ser la base más probada
  con live-build. **"Qué Debian Stable se envía finalmente" queda PENDIENTE** (candidato:
  trixie/Debian 13). El cambio es un **one-liner** en `auto/config` (`--distribution`). Se
  registrará en un ADR cuando se decida.

## Lo que NO está hasta aquí (anti-desborde)

Xfce4 arranca (3A) y el **base está endurecido** (3B.1: hermetismo/telemetría off +
autologin live-only). Aún **sin hardening fino** (3B.2: sysctl de kernel/red, política de
cuentas/PAM), **sin personalización del escritorio** (temas/paneles), sin Calamares/LUKS/TPM,
sin paquetes propios ni CLI dentro de la ISO, y sin navegador (llega por la Vía B / paso de
navegación).
