# ADR-006 — Cadena de arranque del sistema instalado

**Estado:** Aceptado

## Contexto

El Paso 3C hace la ISO **instalable** con Calamares. Por D17 (RF-CORE-05 modificado) el
cifrado de disco completo va por **contraseña LUKS** desde el instalador, y el TPM 2.0 se
desacopla: lo añadirá después un script opcional, `nimbo-tpm-setup`, con
`systemd-cryptenroll`. La cadena de arranque que fije el instalador tiene que **dejar ese
camino abierto sin romper nunca el desbloqueo por contraseña**.

Evidencia (análisis estático de paquetes y fuentes del snapshot `20260901T000000Z`,
[ADR-004](ADR-004-anclaje-temporal-snapshot-debian-org.md)):

- **`systemd-cryptenroll` exige LUKS2.** systemd `252.39-1~deb12u2` lo trae, junto con
  `systemd-cryptsetup` y el plugin `libcryptsetup-token-systemd-tpm2.so`.
- **El Calamares de bookworm (`3.2.61-1+b1`) solo crea LUKS1 y cifra `/boot`.** No tiene
  `luksGeneration`; `KPMHelpers.cpp` usa `FS::luks`, que en kpmcore 22.12.3 ejecuta
  `cryptsetup --type luks1 luksFormat`; y `PartitionLayout.cpp` cifra toda entrada del
  layout cuando hay contraseña (no existe `noEncrypt`).
- **Calamares `3.3.8-1~bpo12+1` (bookworm-backports) sí tiene `luksGeneration` y
  `noEncrypt`**, y todas sus dependencias se satisfacen con bookworm estable.
- **GRUB `2.06-13+deb12u2` abre LUKS2 solo con PBKDF2** (`luks2.mod`: "Argon2 not
  supported"). Si GRUB tiene que abrir el volumen, pide él la contraseña en cada arranque
  y el desbloqueo por TPM no ahorra nada.
- **`initramfs-tools` 0.142 + `cryptsetup-initramfs` 2.6.1 no usan tokens TPM2:** ninguna
  mención a `tpm`/`token`/`systemd-cryptsetup`, y las opciones de crypttab desconocidas se
  descartan (`ignoring unknown option`). **`dracut` 059-4 sí** (`90crypt` +
  `91tpm2-tss`), pero tiene `Conflicts: initramfs-tools`, y `live-boot` necesita
  `initramfs-tools`.
- **No hay systemd-boot firmado en bookworm** (ni en backports); sí `shim-signed`,
  `grub-efi-amd64-signed` y kernel firmado. systemd-boot tampoco arranca en BIOS.
- **Línea base:** la ISO actual arranca en UEFI (QEMU + OVMF, `efi: EFI v2.70 by EDK II`)
  hasta el escritorio Xfce. Verificado el 2026-10-06.

## Decisión

1. **Firmware:** UEFI **obligatorio**; BIOS legacy **opcional** (mejor esfuerzo).
2. **Bootloader:** **GRUB + shim** (`grub-efi-amd64`, `grub-efi-amd64-signed`,
   `shim-signed`; `grub-pc` en BIOS).
3. **Particionado guiado:** **ESP** + **`/boot` ext4 en claro** + **raíz ext4 sobre LUKS2**
   con el KDF por defecto de cryptsetup 2.6.1 (**argon2id**). GRUB nunca abre el LUKS.
   La casilla de cifrado del instalador viene **marcada por defecto**
   (`preCheckEncryption: true`), pero el usuario **puede desmarcarla**: el cifrado es
   opcional. Calamares 3.3.8 no ofrece una opción para forzarlo y no se parchea.
4. **Initramfs en 3C:** **`initramfs-tools`** + `cryptsetup-initramfs` (desbloqueo por
   contraseña). **`nimbo-tpm-setup` cambiará el sistema instalado a `dracut`** cuando el
   usuario opte por el TPM; no es parte de 3C.
5. **Excepción acotada de backports:** el instalador es **Calamares 3.3.8 de
   `bookworm-backports`**, servido por el mismo snapshot. **Solo `calamares`**: el resto
   de backports queda con prioridad negativa, de modo que el build falla si algo más
   intenta entrar. El **sistema instalado no contiene** ni Calamares, ni paquetes de
   backports, ni un `sources.list` con backports. Esto **enmienda** la consecuencia
   "Calamares = la versión que trae bookworm" de
   [ADR-005](ADR-005-quedarse-en-bookworm-v1.md); el resto de ADR-005 sigue vigente.

6. **Pool APT local dentro del squashfs** (`/usr/share/nimbo/pool`, ~8 MiB): los `.deb` de
   GRUB + shim, `grub-pc` y `cryptsetup-initramfs` (los instala el instalador sin red) y
   los de `dracut`, `tpm2-tools` y `libtss2-*` (para `nimbo-tpm-setup`). Como va en el
   squashfs, **viaja al disco instalado**. Se descarta el pool nativo de live-build
   (`*.list.binary`): descarga el cierre completo (~35 MiB) y escribe un `Release` con
   `date -R` y un `Packages.gz` sin `gzip -n`, lo que rompería la reproducibilidad.
7. **`sources.list` del sistema instalado:** una sola fuente,
   `deb [trusted=yes] file:/usr/share/nimbo/pool ./`. Sin mirrors remotos ni backports.
   **Por qué `[trusted=yes]`:** es una fuente **local, sin red**; no hay canal que un
   tercero pueda suplantar, y la integridad de esos `.deb` la da el **hash de la ISO** de
   la que salieron (verificable y reproducible). Es una solución **transitoria**: la
   reemplazará el repositorio firmado con GPG del módulo APT (aptly), junto con
   `nimbo-update-offline`.
8. **Directorio EFI `debian`** (`efiBootloaderId`): la imagen firmada de GRUB de Debian
   lleva embebido el prefijo `/EFI/debian`. Es un nombre técnico en la ESP, no una marca;
   la entrada del menú de arranque sí se llama `nimbo`.

**Opciones descartadas:**

- **B — `/boot` cifrado dentro de la raíz LUKS2 con PBKDF2.** GRUB puede abrirlo, pero
  pide la contraseña él mismo en cada arranque: el TPM no aportaría nada. Además obliga a
  un KDF más débil que argon2id.
- **C — Calamares 3.2.61 tal cual (LUKS1, `/boot` cifrado).** Funciona hoy sin
  backports, pero `systemd-cryptenroll` no admite LUKS1: cierra el camino de D17.
- **D — Instalar en LUKS1 y convertir a LUKS2 después.** Reescribir la cabecera de un
  volumen con datos del usuario es un riesgo que no se asume como plan base.
- **systemd-boot.** Sin binario firmado en bookworm y sin soporte de BIOS.

## Consecuencias

- **`/boot` en claro es superficie de ataque:** kernel e initrd quedan sin cifrar y el
  initrd no va firmado. Con contraseña sola es el compromiso estándar de Debian. Cuando
  entre el TPM, sellar solo a **PCR 7** (el valor por defecto de `systemd-cryptenroll`
  252) **no detecta un initrd manipulado**; el diseño de `nimbo-tpm-setup` deberá elegir
  entre añadir **PCR 9** (re-sellar tras cada kernel o `update-initramfs`, con la
  contraseña como respaldo) o **TPM + PIN** (`--tpm2-with-pin`).
- **PCRs con GRUB** (según documentación de GRUB/TCG, **no medido**): PCR 4 cambia con
  updates de shim/GRUB; PCR 7 con cambios de claves o `dbx` de Secure Boot; **PCR 8 y 9
  cambian con cada kernel** (y PCR 9 con cada `update-initramfs`).
- **La contraseña es siempre el respaldo:** `systemd-cryptenroll` añade un keyslot y un
  token; el keyslot de contraseña creado por el instalador no se toca.
- **`nimbo-tpm-setup` necesita paquetes sin red** (`dracut`, `tpm2-tools`, `libtss2-*`):
  el producto es offline, así que deben viajar con el sistema instalado.
- **`[trusted=yes]` desactiva la verificación de firma de APT para el pool local.** Es
  aceptable solo mientras la fuente sea local y la ISO se verifique por hash; no debe
  copiarse a ninguna fuente remota.
- **El cifrado es opcional:** quien desmarque la casilla obtiene un sistema sin LUKS, y
  `nimbo-tpm-setup` no tendrá nada que vincular. La guía de instalación lo advierte.
- **Backports entra en la receta:** un origen APT más, anclado al mismo snapshot. La
  compuerta `repro-verify.yml` debe seguir en **MATCH**; sin MATCH no hay merge.
- **Reversible:** quitar la excepción devuelve a Calamares 3.2.61 (opción C), a costa de
  D17.

## No verificado

- **Secure Boot activo**, tanto en la ISO como en el sistema instalado. Queda en la lista
  de pruebas; no bloquea 3C.
- Que **dracut 059 + systemd 252** desbloqueen por TPM2 en bookworm y caigan a contraseña
  si el TPM falla (se valida en el paso de `nimbo-tpm-setup`, con QEMU + swtpm).
- Los **PCRs** de la tabla anterior: vienen de documentación, no de mediciones.
- El arranque en **BIOS legacy** del sistema instalado.

## Fecha

2026-10-06
