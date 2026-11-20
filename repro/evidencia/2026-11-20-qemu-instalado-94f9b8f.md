# Evidencia — ISO de `94f9b8f` instalada en QEMU con Secure Boot y LUKS (2026-11-20)

Aprobación en QEMU del candidato a release `v1.0.0`. Esta ISO es la de CI de `94f9b8f`
(merge de #107, `nimbo-nav` 0.1.5-1), con MATCH ×2. Es la primera candidata con los cinco
módulos propios y el hardening 3B.2 dentro (ADR-020) y con los hallazgos del ensayo cerrados
(#101–#105, #107). Se instaló con el lanzador cifrado y se pasó `verificar-instalado
--secure-boot` en el sistema instalado.

## Aprobación (formato fijo)

`release.yml` comprueba este bloque: que existe en `main` y que nombra el hash exacto que se va
a firmar. No cambies el formato sin cambiar el workflow.

```
NIMBO_APROBACION_QEMU
iso_sha256: 63eeb31a33c4a9d4a6597573a6f567d66b6afbbb207286ae7920197414cc0f10
commit: 94f9b8fec60938baccae984f891cc3ac6960e109
run_build_iso: 44654170836
run_repro_verify: 44654170829
verificar_instalado: OK — 0 fallos
secure_boot: exigido
fecha: 2026-11-20
aprobado_por: Juan José (@Duque-Londono)
NIMBO_APROBACION_QEMU_FIN
```

## Procedencia del hash

| | |
|---|---|
| Artifact de CI | `nimbo-iso-94f9b8f`, run `44654170836` (`build-iso`, push a `main`), caduca el 2026-11-27 01:41 UTC |
| Copia local usada en QEMU | `repro/out/ci-main-94f9b8f/nimbo-iso-94f9b8f/live-image-amd64.hybrid.iso` (fuera de git), 572 522 496 bytes |
| `sha256sum` de esa copia (recalculado el 20-nov) | `63eeb31a33c4a9d4a6597573a6f567d66b6afbbb207286ae7920197414cc0f10` |
| `repro-verify`, run `44654170829` | pierna A y pierna B: el mismo hash, `boot_id` distintos → **MATCH** |

El lanzador imprime el hash recortado. El hash completo sale de recalcularlo sobre la misma
copia y de contrastarlo con las dos piernas de CI.

## Cómo se hizo

- Arnés `iso/live-build/install-in-qemu.sh`, variante `v100final` (`NIMBO_VARIANTE=v100final`),
  con `--secure-boot`: OVMF de bookworm con las llaves de Microsoft inscritas y SMM. Disco
  nuevo: la variante no existía antes de esta instalación.
- **Instalación:** escritorio live → "Instalar nimbo (cifrado, recomendado)". La contraseña
  LUKS la tecleó Juan José en la VM; no pasa por ningún registro.
- **Arranque del instalado** sin ISO: pide la contraseña LUKS y llega al greeter de lightdm sin
  entrar solo (D14). Luego: `sudo mount -o ro /dev/vdb1 /mnt && sudo sh /mnt/verificar-instalado.sh --secure-boot`.
- Capturas de todo el tráfico del guest durante la instalación y durante el arranque del
  instalado (`NIMBO_PCAP`).
- Horario: 20-nov, de 06:44 a 06:49 (-05:00).

## Resultados

`verificar-instalado`: **VEREDICTO: OK — 0 fallos** ([informe completo](2026-11-20-qemu-instalado-94f9b8f/informe-verificar-instalado.txt)).

| Sección | Resultado |
|---|---|
| 1. Cifrado | LUKS2, `aes-xts-plain64`, PBKDF argon2id; crypttab sin fichero de clave (pide contraseña); `/` sobre el volumen cifrado; `/boot` en claro y separado; arranque UEFI |
| 2. Initramfs | `cryptsetup`, `cryptroot` y el teclado de consola dentro; sin scripts de live-boot |
| 2b. Secure Boot | `SecureBoot=1`, `SetupMode=0`; el kernel dice "Secure boot enabled"; arranca por `shimx64.efi` |
| 3. D14 | sin autologin |
| 4. Hermetismo 3B.1 | temporizadores de `apt` enmascarados; ningún listener fuera de loopback |
| 5. Sin instalador ni live | ni Calamares, ni live-boot/config, ni backports; única fuente APT: el pool local; `dracut` y `tpm2-tools` instalables sin red desde el pool |
| 6. 3C.2 | `es_CO.UTF-8`, `America/Bogota`, `/swapfile` de 513 MB dentro del volumen cifrado |
| 7. RAM en reposo | **395 MiB** (MemTotal − MemAvailable), menos de 500 MB. Medida a los 58 s de arranque, no a los 90 s que pide el verificador para comparar cifras; la ISO de la demo del 17-nov, instalada, dio 383 MiB |
| 8. CLI | `nimbo-audit` 0.1.0-1 instalado, utilizable, con `verify` y el manual |
| 9. Módulos y 3B.2 | `nimbo-red` 0.1.1-1, `nimbo-update-offline` 0.1.2-1, `nimbo-nav` 0.1.5-1, `nimbo-net` 0.1.0-1; `tor`, `nimbo-modo-tor` y `nimbo-leakcheck` no arrancan solos; sin `wg-nimbo` en reposo ni `wg-quick` habilitado; `verify-hardening` **0 fallos (44 comprobaciones)**; `firefox-esr` 140.14.0esr-1~deb12u1 |

**#107 visto a ojo (Juan José):** con el modo Tor apagado, "Navegar por Tor" desde el menú
muestra la notificación *"nimbo: modo Tor — el modo Tor no está activo y el navegador no se
abre. En una terminal: sudo nimbo-red on && sudo nimbo-tor on"* y Firefox no se abre.

**Hermetismo en la red** (contado con `tcpdump -nr` sobre las capturas):

| Captura | Paquetes | Qué son |
|---|---|---|
| [`instalacion.pcap`](2026-11-20-qemu-instalado-94f9b8f/instalacion.pcap) | 18 | DHCP (5), ARP (2), IPv6 local de enlace (11): MLD, DAD, solicitud y anuncio de router |
| [`instalado.pcap`](2026-11-20-qemu-instalado-94f9b8f/instalado.pcap) | 2 | IPv6 local de enlace: MLD (1) y DAD (1) |

**0 DNS, 0 NTP, 0 web, 0 SYN**, igual que en la evidencia de `03ff84c`. El sistema instalado
lleva 415 paquetes ([lista](2026-11-20-qemu-instalado-94f9b8f/paquetes-instalado.txt)); los
16 de más frente a `03ff84c` son los módulos de ADR-020 y sus dependencias (`firefox-esr`,
`tor`, `wireguard-tools`, `xfce4-notifyd`…).

## Qué se redactó

- **UUID** del volumen LUKS y de la partición GPT → `<UUID-REDACTADO>`. No son secretos, pero
  identifican un disco concreto.
- **Códigos de color** de la terminal, eliminados.
- No había credenciales que quitar: el informe no contiene ni la contraseña LUKS ni una clave
  de recuperación (esta instalación no tiene TPM).

Los originales están en `repro/out/ci-main-94f9b8f/` e `iso/live-build/installed-sb-v100final-*`,
ignorados por git. Hashes de los ficheros versionados:
[`SHA256SUMS`](2026-11-20-qemu-instalado-94f9b8f/SHA256SUMS).

## Lo que no cubre

Hardware real y TPM sobre esta ISO (pendiente, `hardware_2026-11-17/`). Cualquier cambio en
`main` cambia el hash: un release de otro commit necesita su propia evidencia de QEMU.
