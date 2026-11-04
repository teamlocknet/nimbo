# security/luks-tpm

Cifrado de disco del sistema instalado: LUKS2 con contraseña desde el instalador (ADR-006)
y **desbloqueo opcional con el TPM 2.0** mediante `nimbo-tpm-setup` (D17, ADR-008).

**Dueño:** Juan José (reparto D18 del 28-oct).

## `nimbo-tpm-setup`

Es opcional y se usa después de instalar. La contraseña del disco **nunca** se borra: si el
TPM no puede abrir, el arranque vuelve a pedirla.

```
sudo nimbo-tpm-setup            # fase 1 (dracut) → reiniciar con la contraseña → fase 2 (sellar)
sudo nimbo-tpm-setup --reseal   # tras actualizar el kernel o el initrd (pide la contraseña)
nimbo-tpm-setup --estado        # solo lectura
```

- **Fase 1:** dracut y tpm2-tools desde el pool local, `tpm2-device=auto` en el crypttab y
  un initrd nuevo. No toca LUKS. Si algo falla, rollback automático.
- **Fase 2:** clave de recuperación (hay que teclearla completa para confirmarla) y sellado
  a PCR 7+9.
- Códigos de salida: 0 OK · 1 error · 2 uso · 3 no aplica (sin cifrar) · 4 comprobación
  previa fallida.
- Estado y log: `/var/lib/nimbo-tpm/`.

Todavía **no va en la ISO**: se prueba entregándolo por el disco auxiliar del arnés
(`iso/live-build/install-in-qemu.sh --secure-boot --tpm arrancar` + `probar-tpm.sh`). La
integración a la ISO va en un PR aparte (checkpoint de receta).

## Evidencia

| Fecha | Qué |
|---|---|
| [2026-10-23](evidencia/2026-10-23-teclado-dracut.md) | Teclado español en el initrd de dracut: riesgo medido y descartado (V2) |
| [2026-11-04](evidencia/2026-11-04-V3-V8.md) | V3–V8 en QEMU + swtpm: sellado, estabilidad, manipulación, actualización, resellado, sin LUKS2 |
| [2026-11-04](evidencia/2026-11-04-h002-codigos-salida.md) | H-002: códigos de salida reales de cryptsetup en los fallos por memoria |

Pendiente: hardware con TPM real (`docs/manuales/verificacion-hardware-real.md`, 17-nov) y
volver a medir el hermetismo tras `nimbo-tpm-setup` (ver ADR-008).
