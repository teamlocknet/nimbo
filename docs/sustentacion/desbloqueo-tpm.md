# Desbloqueo con TPM (`nimbo-tpm-setup`) — RF-CORE-06

**Responsable:** Juan José.

## Qué hace

- **Opcional y posterior a la instalación.** Vincula la clave del disco al chip TPM 2.0 del equipo,
  para que abra solo mientras el arranque no haya cambiado.
- **La contraseña nunca se borra.** Si el TPM se niega, el arranque la pide.
- **Dos fases con un reinicio:** primero prepara el arranque sin tocar el cifrado y, si algo falla,
  lo deshace. Después crea una clave de recuperación que hay que teclear completa, y sella.
- **Sellado a PCR 7+8+9:** Secure Boot y sus llaves (7), órdenes de GRUB y línea del kernel (8), y
  kernel e initrd (9).

**Límite que se declara tal cual:** sin PIN, un equipo robado entero arranca hasta la pantalla de
inicio de sesión; ahí protege la contraseña de usuario.

## Cómo se prueba

En QEMU con Secure Boot y TPM emulado (swtpm). Las contraseñas las teclea una persona y la clave de
recuperación nunca entra al repositorio.

## Qué se midió

| Prueba | Resultado |
|---|---|
| **Ataque:** editar GRUB con `init=/bin/sh`, sellado 7+9 | ❌ **shell de root con el disco abierto, sin contraseña** |
| **El mismo ataque, sellado 7+8+9** | ✅ el TPM se niega y pide la contraseña |
| **Ataque por la consola de GRUB (`c`), sellado 7+8+9** | ✅ el TPM se niega y pide la contraseña (22-nov) |
| Entrada *recovery mode* de GRUB | ✅ el TPM se niega; sin shell de rescate porque root está bloqueado (22-nov) |
| Clave de recuperación al arrancar | ✅ abre el disco (22-nov) |
| V4: 3 arranques seguidos sin teclear | ✅ abre solo |
| V5: `/boot` manipulado | ✅ pide la contraseña y esta abre |
| V6a: manipulación deshecha | ✅ abre solo |
| V6b: actualización legítima | ✅ pide la contraseña y esta abre |
| V7: resellado | ✅ abre solo |
| V8: instalación sin LUKS2 | ✅ mensaje claro y no toca nada (4-nov) |
| Teclado español en el arranque | ✅ 10 de 10 |
| Hermetismo tras activar el TPM | ✅ 0 sospechosos y 0 puertos (10-nov) |

## Hallazgos

1. **Editar GRUB abría el disco (21-nov).** Al escribir la guía de usuario, sospechamos de nuestro
   propio diseño. GRUB mide la línea del kernel en PCR 8 y no lo estábamos sellando. Se reprodujo
   sobre la ISO de `v1.0.0`, con Secure Boot activo, y se corrigió con PCR 8. La ISO y su firma no
   cambian porque el script no viaja dentro.
2. **`--reseal` se negó a sellar un estado falso.** En una prueba se manipuló y regeneró el initrd
   en un mismo arranque. El script lo detectó y no selló, porque el siguiente arranque no habría
   coincidido.

## Lo que falta

- **Hardware con TPM real**, sobre todo que PCR 8 sea estable entre arranques. Todo lo anterior se
  midió en QEMU.
- El script **no va dentro de la ISO**: se entrega por USB. **El del tag `v1.0.0` es anterior al
  arreglo; se usa el de `main`.**
- `--con-pin` existe, pero no está validado.

*Evidencia:* `security/luks-tpm/evidencia/2026-11-22-recuperacion-grub-qemu.md`,
`security/luks-tpm/evidencia/2026-11-21-pcr8-grub.md`,
`security/luks-tpm/evidencia/2026-11-04-V3-V8.md`,
`security/luks-tpm/evidencia/2026-10-23-teclado-dracut.md`,
`security/luks-tpm/evidencia/2026-11-10-hermetismo-post-tpm.md` · *Diseño:* ADR-008 ·
*Manual:* `docs/manuales/desbloqueo-tpm.md`
