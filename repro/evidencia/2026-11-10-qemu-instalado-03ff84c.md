# Evidencia — ISO de `03ff84c` instalada en QEMU con Secure Boot y LUKS (2026-11-10)

Aprobación en QEMU del candidato a release `v1.0.0-rc1`. Esta ISO es la de CI de `03ff84c`
(PR #54, [ADR-018](../../docs/adr/ADR-018-firmware-explicito.md)), con MATCH ×2. Se instaló con
el lanzador cifrado y se pasó `verificar-instalado --secure-boot` en el sistema instalado.

## Aprobación (formato fijo)

`release.yml` comprueba este bloque: que existe en `main` y que nombra el hash exacto que se va
a firmar. No cambies el formato sin cambiar el workflow.

```
NIMBO_APROBACION_QEMU
iso_sha256: 28760694ba8e20d13b98d04435d97937ae4e33ece521d62324c0ed33c484ae90
commit: 03ff84cd1804908cbd1fd7cdb90c0e8c1734a5fa
run_build_iso: 42850483095
run_repro_verify: 42850482997
verificar_instalado: OK — 0 fallos
secure_boot: exigido
fecha: 2026-11-10
aprobado_por: Juan José (@Duque-Londono)
NIMBO_APROBACION_QEMU_FIN
```

## Procedencia del hash

| | |
|---|---|
| Artifact de CI | `nimbo-iso-03ff84c`, run `42850483095` (`build-iso`, push a `main`), caduca el 2026-11-17 16:11 UTC |
| Copia local usada en QEMU | `repro/out/ci-03ff84c/nimbo-iso-03ff84c/live-image-amd64.hybrid.iso` (fuera de git) |
| `sha256sum` de esa copia (recalculado el 11-nov) | `28760694ba8e20d13b98d04435d97937ae4e33ece521d62324c0ed33c484ae90` |
| `repro-verify`, run `42850482997` | pierna A y pierna B: el mismo hash → **MATCH** |

El lanzador imprime el hash recortado (`sha256=28760694ba8e20d1…`). El hash completo sale de
recalcularlo sobre la misma copia y de contrastarlo con las dos piernas de CI.

## Cómo se hizo

- Arnés `iso/live-build/install-in-qemu.sh`, variante `fw` (`NIMBO_VARIANTE=fw`), con
  `--secure-boot`: OVMF de bookworm (snapshot, caché verificada) con las llaves de Microsoft
  inscritas y SMM, y vídeo `bochs-display` a 1280×800.
- **Instalación:** escritorio live → "Instalar nimbo (cifrado, recomendado)". La contraseña
  LUKS la tecleó Juan José en la VM; no pasa por ningún registro.
- **Arranque del instalado** sin ISO: pide la contraseña LUKS y llega al greeter de lightdm sin
  entrar solo (D14). Tras unos 90 s de reposo: `sudo sh /mnt/verificar-instalado.sh --secure-boot`.
- Capturas de todo el tráfico del guest durante la instalación y durante el arranque del
  instalado.
- Horario: 10-nov, de 11:59 a 12:12 (-05:00).

## Resultados

`verificar-instalado`: **VEREDICTO: OK — 0 fallos** ([informe completo](2026-11-10-qemu-instalado-03ff84c/informe-verificar-instalado.txt)).

| Sección | Resultado |
|---|---|
| 1. Cifrado | LUKS2, `aes-xts-plain64`, PBKDF argon2id; crypttab sin fichero de clave (pide contraseña); `/` sobre el volumen cifrado; `/boot` en claro y separado; arranque UEFI |
| 2. Initramfs | `cryptsetup`, `cryptroot` y el teclado de consola dentro; sin scripts de live-boot |
| 2b. Secure Boot | `SecureBoot=1`, `SetupMode=0`; el kernel dice "Secure boot enabled"; arranca por `shimx64.efi` |
| 3. D14 | sin autologin |
| 4. Hermetismo 3B.1 | temporizadores de `apt` enmascarados; ningún listener fuera de loopback |
| 5. Sin instalador ni live | ni Calamares, ni live-boot/config, ni backports; única fuente APT: el pool local |
| 6. 3C.2 | `es_CO.UTF-8`, `America/Bogota`, `/swapfile` de 513 MB dentro del volumen cifrado |
| 7. RAM en reposo | **344 MiB** (MemTotal − MemAvailable), menos de 500 MB |
| 8. CLI | `nimbo-audit` 0.1.0-1 instalado, utilizable, con `verify` y el manual |

**Hermetismo en la red** (contado con `tcpdump -nr` sobre las capturas):

| Captura | Paquetes | Qué son |
|---|---|---|
| [`instalacion.pcap`](2026-11-10-qemu-instalado-03ff84c/instalacion.pcap) | 18 | DHCP (5), ARP (2), IPv6 local de enlace (11): MLD, DAD, solicitud y anuncio de router |
| [`instalado.pcap`](2026-11-10-qemu-instalado-03ff84c/instalado.pcap) | 2 | IPv6 local de enlace: MLD (1) y DAD (1) |

**0 DNS, 0 NTP, 0 web, 0 SYN.** El sistema instalado lleva 399 paquetes
([lista](2026-11-10-qemu-instalado-03ff84c/paquetes-instalado.txt)). Los cambios frente a la
ISO de #42 están en ADR-018.

## Qué se redactó

- **UUID** del volumen LUKS y de la partición GPT → `<UUID-REDACTADO>`. No son secretos, pero
  identifican un disco concreto.
- **Rutas locales** de la máquina de Juan José → relativas al repositorio.
- **Códigos de color** de la terminal, eliminados.
- No había credenciales que quitar: el informe no contiene ni la contraseña LUKS ni una clave
  de recuperación (esta instalación no tiene TPM).

Los originales están en `repro/out/ci-03ff84c/`, ignorado por git. Hashes de los ficheros
versionados: [`SHA256SUMS`](2026-11-10-qemu-instalado-03ff84c/SHA256SUMS).

## Lo que no cubre

Hardware real (17-nov), TPM sobre esta ISO y los módulos todavía fuera de la ISO
(`nimbo-nav`, 3B.2, `nimbo-red`, `nimbo-net`, `nimbo-update-offline`). Al integrarlos cambia
el hash: cualquier release posterior necesita su propia evidencia de QEMU.
