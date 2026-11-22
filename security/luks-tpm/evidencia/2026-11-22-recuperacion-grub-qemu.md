# nimbo-tpm-setup — consola de GRUB, entrada de recuperación y clave de recuperación (2026-11-22)

**Estado:** verde en QEMU + swtpm. Cierra los puntos que la
[evidencia del 21-nov](2026-11-21-pcr8-grub.md) dejó sin probar. Falta repetirlo en hardware con
TPM real (`docs/manuales/verificacion-hardware-real.md`).

## Entorno

- Copia idéntica (`cmp`) del disco, la NVRAM y el estado de swtpm de la prueba del 21-nov:
  ISO de `v1.0.0` (`63eeb31a33c4a9d4a6597573a6f567d66b6afbbb207286ae7920197414cc0f10`) instalada
  con cifrado y sellada a **PCR 7+8+9**. El disco original no se arrancó ni cambió.
- Arnés con `--secure-boot --tpm`, variante `recgrub`, **sin tarjeta de red** (`NIMBO_SIN_RED=1`).
- Juan José tecleó la clave de recuperación, que no pasó por Claude Code. Claude Code solo envió
  por el monitor de QEMU flechas y órdenes de GRUB, y leyó capturas; no tecleó ninguna credencial.

## Resultados

| Prueba | Qué se hizo | Resultado |
|---|---|---|
| **Control inicial** | Arranque normal sin tocar el teclado | ✅ Abrió solo hasta la pantalla de inicio de sesión |
| **Consola de GRUB** | `c`, y a mano `search`, `linux … init=/bin/sh`, `initrd` y `boot` | ✅ El TPM se niega: `Please enter passphrase or recovery key for disk root`. No se tecleó nada |
| **Entrada de recuperación** | *Advanced options* → *recovery mode*, sin editar | ✅ El TPM se niega y pide la contraseña o la clave |
| **Clave de recuperación** | Teclearla en ese mismo arranque | ✅ Abrió el disco y llegó a *rescue mode*. El primer intento no coincidió y el segundo abrió |
| **Sin shell de rescate** | Mirar el final de ese arranque | ✅ `Cannot open access to console, the root account is locked` |
| **Control final** | Arranque normal después de todo lo anterior | ✅ Abrió solo hasta la pantalla de inicio de sesión |

## Observaciones

- En la entrada de recuperación, los mensajes del kernel se mezclan con la petición de la clave.
  Se puede teclear igual, pero a primera vista parece que el arranque sigue solo.
- No se determinó por qué falló el primer intento de la clave. El segundo funcionó.

## Qué se redactó

Las capturas muestran el UUID del volumen, así que quedan fuera de git, en
`repro/out/tpm-recuperacion-2026-11-22/`, con su `SHA256SUMS`. Ninguna muestra la clave de
recuperación. Aquí solo van datos sin credenciales.

## Límites

- QEMU + swtpm, no un TPM real.
- No se validó `--con-pin`.
- Con la clave correcta, el modo de recuperación abre el disco, pero no da una shell porque root
  está bloqueado. No se probó ninguna otra forma de entrar desde ese modo.
