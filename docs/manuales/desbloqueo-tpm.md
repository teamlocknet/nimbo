# Manual — Desbloquear el disco con el TPM (`nimbo-tpm-setup`)

**Para:** quien usa un equipo nimbo instalado con cifrado. **Requisitos:** RF-CORE-06,
RNF-06. **Diseño:** [ADR-008](../adr/ADR-008-desbloqueo-tpm-opcional.md).
**Detalle técnico:** [`security/luks-tpm`](../../security/luks-tpm/README.md).

Es **opcional**. Sin esto, nimbo pide la contraseña del disco en cada arranque y funciona
igual. Con esto, el chip TPM del equipo abre el disco solo mientras el arranque no haya
cambiado. **Tu contraseña nunca se borra:** si el TPM se niega, el arranque te la pide.

> **Estado:** validado en máquina virtual con TPM emulado. La prueba en hardware con TPM real
> está pendiente. No lo actives todavía en un equipo con datos importantes.

## Antes de empezar

- nimbo instalado **con cifrado**, arranque **UEFI** y **Secure Boot activo**.
- **TPM 2.0** activado en el firmware. Compruébalo con `cat /sys/class/tpm/tpm0/tpm_version_major`:
  debe responder `2`.
- **Papel y lápiz** para la clave de recuperación.
- Una **USB** con el script, porque no viene dentro de la ISO. **No uses el del tag `v1.0.0`:**
  es anterior a un arreglo de seguridad. Desde otro equipo con internet, descarga
  [esta versión](https://raw.githubusercontent.com/teamlocknet/nimbo/725eebeb19d9d295013d3174daaa5af8dbcb7808/security/luks-tpm/nimbo-tpm-setup)
  y cópiala a la USB.

Conecta la USB, mira su nombre con `lsblk` y móntala, cambiando `sdX1` por el tuyo:

```
sudo mount -o ro /dev/sdX1 /mnt
sha256sum /mnt/nimbo-tpm-setup
```

El resultado debe ser exactamente:
`139e6e811cdca953275d89e615833355d8b7c0447395d3fd7b683da714764047`. Si no coincide, **no lo
ejecutes**.

## Activarlo (dos fases, 15 min)

**Fase 1, preparar.** No toca el cifrado. Si algo falla, deshace sus cambios:

```
sudo sh /mnt/nimbo-tpm-setup
```

Debe decir `FASE 1 COMPLETA`. Reinicia con `sudo reboot`. El disco pide la contraseña como
siempre: comprueba que entra con tu teclado. **No actualices nada antes de la fase 2.**

**Fase 2, sellar.** Vuelve a montar la USB y ejecuta lo mismo:

```
sudo mount -o ro /dev/sdX1 /mnt
sudo sh /mnt/nimbo-tpm-setup
```

1. Te pide la contraseña del disco y muestra una **clave de recuperación**.
2. **Anótala en papel. No le tomes foto ni la guardes en un fichero.**
3. Tecléala completa cuando te la pida. Si no la confirmas, se borra y no se sella nada.
4. Te pide otra vez la contraseña del disco.

Debe decir `FASE 2 COMPLETA`. Al reiniciar, el equipo debe llegar a la pantalla de inicio de
sesión **sin pedir la contraseña del disco**.

## Uso diario

| Quiero… | Comando |
|---|---|
| Ver el estado | `sudo sh /mnt/nimbo-tpm-setup --estado` |
| Volver a sellar tras una actualización | `sudo sh /mnt/nimbo-tpm-setup --reseal` |

## Si el arranque vuelve a pedir la contraseña

Es el comportamiento previsto cuando cambia algo en el arranque. El TPM se niega por:

- una actualización del kernel, del initrd o de la configuración de GRUB;
- una actualización del firmware o de las llaves de Secure Boot;
- **alguien manipuló `/boot` o editó el menú de GRUB.**

**Si no actualizaste nada, no lo des por normal:** puede ser una manipulación. No vuelvas a
sellar hasta saber qué cambió, porque el sellado confiaría en el arranque actual.

Si actualizaste tú, teclea la contraseña o la clave de recuperación. Ya dentro, con la USB
montada, ejecuta `sudo sh /mnt/nimbo-tpm-setup --reseal`. Debe decir `RESELLADO COMPLETO`.

## Mensajes frecuentes

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| `Secure Boot no está activo` | El firmware no verifica el arranque | Actívalo en el firmware |
| `no hay TPM` | El firmware no lo expone | Actívalo en el firmware |
| `Instalación SIN cifrar` | No hay nada que vincular | Nada: no aplica |
| `este arranque no pasó por el initrd de dracut` | Falta reiniciar tras la fase 1 | Reinicia y repite |
| `el initrd se modificó después de este arranque` | Hubo un cambio sin reiniciar | Reinicia con la contraseña y repite `--reseal` |
| `hay un kernel más nuevo` | Aún no arrancaste en él | Reinicia y repite `--reseal` |

Códigos de salida: `0` bien · `1` error · `2` orden mal escrita · `3` no aplica (sin cifrar) ·
`4` comprobación previa fallida, sin cambios. Registro: `/var/lib/nimbo-tpm/nimbo-tpm-setup.log`.

## Lo que NO hace (límites declarados)

- **Sin PIN, un equipo robado entero arranca hasta la pantalla de inicio de sesión.** El disco
  ya está abierto y lo que protege entonces es tu contraseña de usuario. Si ese riesgo te
  importa, sigue usando solo la contraseña del disco.
- La opción `--con-pin` existe, pero **no se ha validado**. No cuentes con ella.
- Si sellaste antes del 21-nov-2026 (PCR 7+9), editar GRUB puede abrir tu disco. **Ejecuta
  `--reseal` con la versión de esta guía** para quedar en PCR 7+8+9.

## Cómo se verificó

Sobre la ISO de `v1.0.0` en QEMU, con Secure Boot y TPM emulado (21-nov,
[evidencia](../../security/luks-tpm/evidencia/2026-11-21-pcr8-grub.md)):

| Prueba | Resultado |
|---|---|
| 3 arranques seguidos sin teclear | ✅ abre solo |
| Editar GRUB con `init=/bin/sh` | ✅ el TPM se niega y pide la contraseña |
| `/boot` manipulado | ✅ pide la contraseña y esta abre |
| Manipulación deshecha | ✅ abre solo |
| Actualización legítima y `--reseal` | ✅ pide la contraseña y, tras resellar, abre solo |
| Abrir el disco con la clave de recuperación al arrancar | *Pendiente: hardware real* |
| Todo lo anterior con un TPM real | *Pendiente: [guion de hardware](verificacion-hardware-real.md)* |
