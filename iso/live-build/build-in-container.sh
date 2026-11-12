#!/usr/bin/env bash
# build-in-container.sh — construye la ISO live mínima dentro de un contenedor
# Debian bookworm, aislando la toolchain de Debian del host.
#
# Motor de contenedor agnóstico (paridad dev/CI):
#   - Local (Fedora):   CONTAINER_ENGINE=podman (por defecto). DEBE correr rootful,
#                       porque debootstrap crea device nodes (mknod), imposible en
#                       podman rootless:
#                           sudo ./build-in-container.sh
#   - CI (ubuntu):      CONTAINER_ENGINE=docker ./build-in-container.sh
#                       (el runner permite --privileged sin sudo)
#
# La LÓGICA DE BUILD es idéntica en ambos: solo cambia el motor. No se reinventa
# la receta (misma imagen, mismo apt-get install live-build && lb config && lb build).
#
# Salida: live-image-amd64.hybrid.iso (en esta misma carpeta)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
# Módulos propios (ADR-020): se compilan de packages/<módulo>/ según la lista única
# config/includes.chroot/usr/share/nimbo/modulos.list. El hardening 3B.2 se copia de
# security/hardening/3b2/ (una sola fuente; ADR-014). Ambos se montan de solo lectura.
PACKAGES_SOURCE="$(cd "$HERE/../../packages" && pwd)"
HARDENING_SOURCE="$(cd "$HERE/../../security/hardening/3b2" && pwd)"
SRC_VOL=":ro"
[ "${CONTAINER_ENGINE:-podman}" != podman ] || SRC_VOL=":ro,Z"

# --- Motor de contenedor -------------------------------------------------------
ENGINE="${CONTAINER_ENGINE:-podman}"
command -v "$ENGINE" >/dev/null || { echo "ERROR: no está instalado el motor '$ENGINE'"; exit 1; }

# :Z (relabel SELinux) solo aplica a podman en hosts con SELinux (Fedora); docker
# en Ubuntu no lo necesita.
VOL_OPT=""
[ "$ENGINE" = "podman" ] && VOL_OPT=":Z"

# -t (tty) solo si hay terminal interactiva (en CI no la hay).
TTY_OPT=()
[ -t 1 ] && TTY_OPT=(-t)

# --- Imagen base del contenedor ------------------------------------------------
# Anclada por DIGEST del índice multi-arch (reproducibilidad; docker y podman
# resuelven el amd64 desde el mismo índice). Forma solo-digest (canónica, aceptada
# por todos los motores). Este digest corresponde al tag debian:bookworm-slim.
# Sobreescribible con NIMBO_BASE_IMAGE=... ./build-in-container.sh
IMAGE="${NIMBO_BASE_IMAGE:-docker.io/library/debian@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171}"

# --- Determinismo de tiempo ----------------------------------------------------
# SOURCE_DATE_EPOCH: se respeta si viene del entorno (CI lo pasa explícito); si no,
# se calcula desde el commit HEAD. -c safe.directory='*' evita el aviso de "dubious
# ownership" al correr con sudo sobre un repo de otro usuario.
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(git -c safe.directory='*' -C "$HERE" log -1 --pretty=%ct 2>/dev/null || date +%s)}"
export SOURCE_DATE_EPOCH

# --- Anclaje temporal: fuente ÚNICA del timestamp (Paso 1C.6, ver ADR-004) -----
# snapshot.env define NIMBO_SNAPSHOT; lo sourcean TANTO este script (para anclar la
# toolchain, abajo) como auto/config (para los mirrors del producto). Un solo sitio.
. "$HERE/snapshot.env"
export NIMBO_SNAPSHOT

echo ">> Motor             : $ENGINE"
echo ">> Imagen base       : $IMAGE"
echo ">> Snapshot (anclaje): $NIMBO_SNAPSHOT  (toolchain + producto)"
# Espejo parcial propio (ADR-016): si NIMBO_ESPEJO viene del entorno, toolchain y producto
# se descargan de repro/espejo/espejo.py (mismos bytes del snapshot, firma intacta).
export NIMBO_ESPEJO="${NIMBO_ESPEJO:-}"
echo ">> Origen paquetes  : ${NIMBO_ESPEJO:-snapshot.debian.org (directo)}"
echo ">> SOURCE_DATE_EPOCH  : $SOURCE_DATE_EPOCH ($(date -u -d "@$SOURCE_DATE_EPOCH" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo '?'))"
echo ">> Directorio montado : $HERE -> /build"

# --- Sistema de archivos del directorio de build (ADR-007, hallazgo H-001) -------
# El chroot vive aquí, así que hereda este sistema de archivos. En btrfs los directorios
# tienen nlink=1 y eso se filtraba al initrd (cpio newc guarda nlink): la ISO salía
# distinta de la de CI (ext4). Lo cierra el hook 9990-nimbo-initrd-tmpfs, cuyo
# auto-chequeo FALLA el build si la filtración reaparece. Aquí solo se AVISA: el build es
# correcto, pero es un anfitrión distinto del de CI y la prueba es comparar el SHA-256.
FS_BUILD="$(stat -f -c %T "$HERE" 2>/dev/null || echo desconocido)"
echo ">> Sistema de archivos: $FS_BUILD"
if [ "$FS_BUILD" = "btrfs" ]; then
    echo
    echo "!! ================================================================================"
    echo "!! AVISO: el directorio de build está en BTRFS."
    echo "!!   btrfs da nlink=1 a los directorios; antes eso se filtraba al initrd y la ISO"
    echo "!!   no coincidía con la de CI (ext4). Mitigado por el hook 9990-nimbo-initrd-tmpfs"
    echo "!!   (initrd generado sobre tmpfs + auto-chequeo). Ver ADR-007 y H-001."
    echo "!!   Para afirmar reproducibilidad, COMPARA el SHA-256 de esta ISO con el de CI."
    echo "!! ================================================================================"
fi
echo

# --- Build ---------------------------------------------------------------------
# --privileged : live-build usa debootstrap/chroot/mknod.
# --network=host: el contenedor debe alcanzar los mirrors de Debian (en Fedora el
#                 podman rootful no resuelve DNS con su backend propio; en CI iguala
#                 el comportamiento).
exec "$ENGINE" run --rm "${TTY_OPT[@]}" \
    --privileged \
    --network=host \
    -v "$HERE":/build"$VOL_OPT" \
    -v "$PACKAGES_SOURCE:/src/packages$SRC_VOL" \
    -v "$HARDENING_SOURCE:/src/hardening-3b2$SRC_VOL" \
    -w /build \
    -e SOURCE_DATE_EPOCH \
    -e NIMBO_SNAPSHOT \
    -e NIMBO_ESPEJO \
    -e TZ=UTC \
    -e LC_ALL=C.UTF-8 \
    -e DEBIAN_FRONTEND=noninteractive \
    "$IMAGE" \
    bash -euo pipefail -c '
        # --- Anclar la TOOLCHAIN al mismo snapshot (Paso 1C.6, ver ADR-004) --------
        # El apt de bookworm-slim apunta por defecto a deb.debian.org (rolling): el
        # paquete live-build que se instalara ahi podria cambiar con un point-release
        # y romper la reproducibilidad temporal. Lo anclamos al MISMO snapshot que el
        # producto. http (no https): bookworm-slim no trae ca-certificates todavia
        # (se instala en este mismo apt-get); la seguridad la da la firma GPG, que apt
        # sigue verificando (NO se toca apt-secure). Solo se necesita debian/main.
        printf "deb %s/archive/debian/%s/ bookworm main\n" "${NIMBO_ESPEJO:-http://snapshot.debian.org}" "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
        rm -f /etc/apt/sources.list.d/debian.sources   # quita el default deb822 si existe
        printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" > /etc/apt/apt.conf.d/99nimbo-snapshot
        echo ">> Toolchain anclada a snapshot $NIMBO_SNAPSHOT (http, GPG intacta)"
        apt-get update
        apt-get install -y --no-install-recommends live-build ca-certificates \
            build-essential fakeroot debhelper dh-python pybuild-plugin-pyproject \
            python3-all python3-setuptools python3-pytest python3-typer
        # Compilar cada módulo de la lista desde la fuente montada de solo lectura; sin
        # Docker anidado. Las Build-Depends salen del debian/control de cada módulo.
        MODULOS="$(grep -v "^[[:space:]]*#" config/includes.chroot/usr/share/nimbo/modulos.list | grep -v "^[[:space:]]*$")"
        mkdir -p /tmp/nimbo-package
        for m in $MODULOS; do
            cp -a "/src/packages/$m" "/tmp/nimbo-package/$m"
            apt-get build-dep -y "/tmp/nimbo-package/$m"
            (cd "/tmp/nimbo-package/$m" && dpkg-buildpackage -us -uc -b)
        done
        cd /build
        lb clean --purge || true
        lb config
        # Solo los paquetes propios entran en el repositorio temporal nativo de live-build:
        # exactamente un .deb por módulo, Architecture all.
        mkdir -p config/packages.chroot
        find config/packages.chroot -maxdepth 1 -type f -name "*.deb" -delete
        for m in $MODULOS; do
            set -- /tmp/nimbo-package/"$m"_*.deb
            [ "$#" -eq 1 ] && [ -f "$1" ] || { echo "ERROR: $m no dejó exactamente un .deb" >&2; exit 1; }
            [ "$(dpkg-deb -f "$1" Package)" = "$m" ]
            [ "$(dpkg-deb -f "$1" Architecture)" = all ]
            dpkg-deb -f "$1" Package Version Architecture Depends
            sha256sum "$1"
            cp "$1" config/packages.chroot/
        done
        [ "$(find /tmp/nimbo-package -maxdepth 1 -name "*.deb" | wc -l)" -eq "$(printf "%s\n" $MODULOS | wc -l)" ] \
            || { echo "ERROR: hay .deb de más en /tmp/nimbo-package" >&2; exit 1; }
        # Hardening 3B.2 (ADR-014): sysctl, faillock, perfiles PAM y verificador, copiados
        # con permisos explícitos. Los activa el hook 0170. Ficheros generados: no se versionan.
        H=/src/hardening-3b2; I=config/includes.chroot
        install -D -m 0644 "$H/sysctl/99-zz-nimbo-hardening.conf" "$I/etc/sysctl.d/99-zz-nimbo-hardening.conf"
        install -D -m 0644 "$H/sysctl/99-zz-nimbo-hardening.conf" "$I/usr/share/nimbo/hardening/99-zz-nimbo-hardening.conf"
        install -D -m 0644 "$H/pam/faillock.conf" "$I/etc/security/faillock.conf"
        install -D -m 0644 "$H/pam/nimbo-faillock" "$I/usr/share/pam-configs/nimbo-faillock"
        install -D -m 0644 "$H/pam/nimbo-faillock-preauth" "$I/usr/share/pam-configs/nimbo-faillock-preauth"
        install -D -m 0755 "$H/verify-hardening.sh" "$I/usr/lib/nimbo/verify-hardening"
        lb build
        echo
        # Segunda barrera: auto/build ya corta en la etapa que falla, pero si lb build
        # terminara sin ISO, el script tiene que salir con error, no solo avisar.
        if ! ls live-image-*.iso >/dev/null 2>&1; then
            echo "ERROR: lb build terminó sin generar la ISO — revisar binary.buildlog" >&2
            exit 1
        fi
        echo ">> Build terminado. ISO:"
        ls -lh live-image-*.iso
    '
