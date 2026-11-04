# Riesgo MEDIDO Y DESCARTADO — teclado español en el initrd de dracut (2026-10-23)

**Estado:** descartado con medición. No es un riesgo abierto.

## El riesgo

`nimbo-tpm-setup` (fase 1) cambia el initrd de `initramfs-tools` a **dracut**. Si el initrd
de dracut no cargara la distribución de teclado del sistema, la contraseña LUKS se
interpretaría con la de EE. UU. y cualquier símbolo que cambie de tecla (`ñ`, `-`, `/`…)
haría fallar el desbloqueo. Dos sospechas concretas:

1. El módulo upstream `10i18n` de dracut necesita `/etc/vconsole.conf` y keymaps de `kbd`,
   y el `kbd` de bookworm no trae ninguno (0 ficheros `keymaps/*.map`).
2. Aunque el teclado se cargue, en modo systemd el prompt de `systemd-cryptsetup` arranca en
   paralelo con el job de udev que lo carga (1,53 s frente a 1,61 s en el journal): podría
   haber una carrera.

## Lo que lo cierra

- **Diseño (sospecha 1):** el dracut de Debian trae su propio módulo **`09console-setup`**,
  que ejecuta `setupcon --setup-dir` y lleva al initrd el teclado de `/etc/default/keyboard`.
  La fase 1 lo fuerza (`add_dracutmodules+=" … console-setup "`) y quita `10i18n`.
  Verificado en el initrd generado: `etc/console-setup/cached_UTF-8_del.kmap` y
  `usr/lib/udev/console-setup` presentes.
- **Medición (sospecha 2):** `iso/live-build/medir-desbloqueo.sh`, 10 arranques del disco de
  prueba con dracut (Secure Boot activo, swtpm, 2048 MiB), tecleando una **clave de prueba
  generada** que contiene `ñ`, `Ñ`, `-` y `/` **en el instante en que el prompt aparece en
  pantalla** (`--retardo 0`). Se envía con `sendkey` como **teclas físicas de un teclado
  español**: si el initrd tuviera la distribución de EE. UU., esas mismas teclas producirían
  otros caracteres y el desbloqueo fallaría.

| Arranques | Prompt en pantalla | Desbloqueó | Tiempo tras teclear |
|---|---|---|---|
| 10 | 4,0–4,3 s | **10 / 10** | 5,4–6,6 s |

Cada desbloqueo se comprobó con la captura final (greeter de lightdm), no solo con la
métrica de la pantalla. La verificación con los ojos (V2, Juan José) coincide: prompt de
dracut, pantalla limpia, contraseña con símbolos aceptada.

## Límites

- Lo medido es el peor caso realista para una persona: teclear en cuanto el prompt se ve.
  Teclas pulsadas *antes* de que aparezca el prompt no son un caso de uso.
- Teclado español (`XKBLAYOUT="es"`). Otras distribuciones siguen el mismo camino
  (`setupcon`), pero no se han medido.
- QEMU con `sendkey`; en hardware real se comprueba con los ojos el 17-nov
  (`docs/manuales/verificacion-hardware-real.md`).

La clave de prueba no aparece en esta evidencia ni en el repo (regla de credenciales).
