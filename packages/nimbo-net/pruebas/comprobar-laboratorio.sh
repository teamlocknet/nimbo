#!/usr/bin/env bash
# Preflight pasivo: no instala, no arranca VMs ni configura red.
set -euo pipefail
faltan=0
for herramienta in qemu-system-x86_64 qemu-img xorriso python3; do
    if command -v "$herramienta" >/dev/null; then
        printf "OK: %s disponible\n" "$herramienta"
    else
        printf "FALTA: %s\n" "$herramienta"
        faltan=1
    fi
done
if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
    echo "ACELERACION: KVM disponible para el usuario"
else
    echo "ACELERACION: sin KVM; usar TCG (emulacion por software, mas lenta)"
fi
awk '/^MemAvailable:/{printf "RAM disponible WSL: %.1f GiB\n", $2/1048576}' /proc/meminfo
if [ "$#" -gt 0 ]; then
    test -r "$1" || { echo "ERROR: ISO no legible" >&2; exit 1; }
    sha256sum -- "$1"
    echo "La ISO base no incluye nimbo-net/wireguard-tools hasta su integracion aprobada."
fi
exit "$faltan"
