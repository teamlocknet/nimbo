# ADR-008 — Desbloqueo opcional del disco con el TPM (`nimbo-tpm-setup`)

**Estado:** Aceptado

## Contexto

D17: el disco del sistema instalado es LUKS2 con contraseña desde el instalador (Calamares,
ADR-006), y el vínculo al TPM 2.0 es **opcional** y posterior a la instalación. Hace falta
decidir cómo se sella la clave, con qué herramientas y qué pasa cuando el arranque cambia.

Restricciones:

- **bookworm** (ADR-005): systemd 252, cryptsetup 2.6.1. El `cryptroot` de initramfs-tools
  (camino por defecto del producto) **no** sabe usar tokens TPM2 de systemd.
- **Sin red ni telemetría:** todo lo que se instale tiene que salir del pool APT local de
  la ISO.
- **Nunca dejar a nadie fuera de su disco:** la contraseña tiene que seguir valiendo siempre.
- `/boot` va en claro (ADR-006). Por eso el sellado tiene que detectar que alguien cambió
  el kernel o el initrd.

Opciones consideradas:

1. **clevis** (`clevis-luks` + `clevis-initramfs`): encaja con initramfs-tools, pero es otra
   pila (JOSE, pin `tpm2`), no usa el token nativo de systemd y añade más paquetes.
2. **systemd-cryptenroll + dracut:** el token `systemd-tpm2` es el formato nativo de LUKS2
   en systemd 252. dracut 059 lleva `systemd-cryptsetup` al initrd y lee ese token.
   Cambiar de initramfs-tools a dracut solo ocurre en los equipos que eligen el TPM.
3. **systemd-boot / UKI con PCR 11 firmados:** es la vía moderna, pero cambia la cadena de
   arranque (GRUB+shim, ADR-006) y no está madura en bookworm.

## Decisión

Se usa **systemd-cryptenroll + dracut**, con un script `nimbo-tpm-setup` en **dos fases y
un reinicio entre ellas**, sellado a **PCR 7+9** (desde el 21-nov, **PCR 7+8+9**: ver la
Enmienda):

- **PCR 7** (estado de Secure Boot y sus llaves) + **PCR 9** (lo que GRUB lee de `/boot`:
  kernel e initrd). Cambiar cualquier byte del initrd hace que el TPM se niegue.
- **Fase 1:** instala dracut y tpm2-tools desde el pool local, pone `tpm2-device=auto` en el
  crypttab y regenera el initrd. **No toca LUKS.** Si algo falla, hay rollback automático a
  initramfs-tools. Después se reinicia con la contraseña, para validar dracut y el teclado
  antes de que el TPM entre en juego.
- **Fase 2:** crea la clave de recuperación, exige teclearla **completa** y comprueba que
  abre su keyslot (si no, la borra y no sella nada). Luego sella y verifica con
  `--token-only`.
- **Secure Boot exigido** (con `--sin-secure-boot`, avisa fuerte y sigue). PIN opcional
  (`--con-pin`).
- **Resellado manual** con `--reseal` tras una actualización legítima. Se niega si el initrd
  cambió después del arranque actual o si hay un kernel más nuevo sin arrancar.
- La contraseña de la instalación **nunca** se borra.

Se valida en QEMU + swtpm (V2–V8) antes del hardware real. La integración de
`nimbo-tpm-setup` a la ISO va en un PR aparte: cambia el SHA y es checkpoint de receta.

## Consecuencias

**Se gana:**

- Desbloqueo sin teclear en el equipo de siempre.
- Si `/boot` se manipula (V5) o cambia legítimamente (V6b), el TPM se niega y vuelve a
  pedir la contraseña. Medido en `security/luks-tpm/evidencia/2026-11-04-V3-V8.md`.
- Los equipos que no usan TPM no cambian nada: siguen con initramfs-tools.

**Se paga:**

- **Hay que resellar tras cada actualización de kernel o initrd** (`--reseal`, con la
  contraseña). Hasta entonces el arranque pide contraseña. No hay resellado automático:
  un resellado desatendido sellaría también un initrd manipulado.
- **Dos initramfs posibles** en el producto: initramfs-tools por defecto y dracut tras
  `nimbo-tpm-setup`. Los mensajes de H-002 (ADR-009) solo cubren initramfs-tools.
- **Paquetes añadidos por la fase 1:** dracut, dracut-core, tpm2-tools y las libtss2.
  `libtss2-fapi1` arrastra **`libcurl4`** (la usa la API FAPI para descargar certificados
  de fabricantes). nimbo no usa FAPI ni la invoca nada, pero es una biblioteca de red más
  en el sistema. **Medido el 10-nov** en un sistema que ya pasó por `nimbo-tpm-setup`:
  0 paquetes sospechosos, 0 puertos escuchando y ningún proceso con `libcurl` cargada
  (`security/luks-tpm/evidencia/2026-11-10-hermetismo-post-tpm.md`). Falta repetirlo en
  hardware real.
- **PCR 9 depende de lo que lea GRUB:** si `grubenv` cambiara en cada arranque, el TPM nunca
  abriría. En QEMU no ocurrió en 9 arranques. Hay que confirmarlo en hardware real.
- **PCR 7 en hardware real:** una actualización del firmware o de las llaves de Secure Boot
  cambia el PCR 7 y obliga a usar la contraseña y `--reseal`.

## Enmienda (2026-11-21, Juan José): sellado a PCR 7+8+9

**Sustituye al sellado a PCR 7+9 de la Decisión.** Con PCR 7+9, editar el menú de GRUB
(`init=/bin/sh`) arrancaba una shell de root con el disco abierto por el TPM y sin pedir
ninguna contraseña: GRUB mide sus órdenes y la línea del kernel en **PCR 8**, que no estaba
sellado. Reproducido en QEMU sobre la ISO de `v1.0.0`
(`security/luks-tpm/evidencia/2026-11-21-pcr8-grub.md`).

- **Decisión:** sellar también a PCR 8, en la fase 2 y en `--reseal`. Se descarta poner
  contraseña a GRUB porque añade otra credencial que custodiar.
- **Se gana:** cualquier edición de la línea del kernel hace que el TPM se niegue y pida la
  contraseña. Medido: el ataque ya no abre, y V4 a V7 siguen en verde.
- **Se paga:** un cambio en `grub.cfg` también obliga a usar la contraseña y `--reseal`.
- **Migración:** un disco sellado a PCR 7+9 sigue expuesto hasta ejecutar `--reseal` con el
  script corregido. El script del tag `v1.0.0` es anterior a este arreglo; la ISO no lo lleva.
- **Pendiente:** confirmar en hardware real que PCR 8 es estable entre arranques.

## Fecha

2026-11-04 (enmienda: 2026-11-21)
