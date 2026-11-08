# ADR-009 — Mensajes honestos cuando el desbloqueo del disco falla por memoria (H-002)

**Estado:** Aceptado (mensajes: 4-nov; RAM mínima, decisión E: 8-nov).

## Contexto

H-002: el disco instalado usa LUKS2 con argon2id. Calamares 3.3.8 no deja elegir los
parámetros de PBKDF, así que cryptsetup calibra en la máquina instaladora (hasta 1 GiB de
memoria). Si después se arranca con menos RAM, el desbloqueo falla, y el `cryptroot` de
Debian (initramfs-tools) imprime en todos los casos *"cryptsetup failed, bad password or
options?"*. La persona cree que se equivocó de contraseña y repite.

Medido (`security/luks-tpm/evidencia/2026-11-04-h002-codigos-salida.md`): cryptsetup
2.6.1 devuelve **2** si la contraseña es incorrecta, **3** si no hay memoria para argon2id y
**137** si el kernel lo mata por falta de memoria. `cryptroot` recibe ese código en `rv`,
pero el mensaje lo ignora.

Opciones:

1. **Avisar antes del prompt:** leer de la cabecera la memoria que exige el keyslot más
   exigente y compararla con `MemAvailable`.
2. **Explicar después del fallo:** un envoltorio de `/sbin/cryptsetup` dentro del initrd que
   lee el código real.
3. **Parchear `cryptroot`** para cambiar su mensaje: es más limpio en pantalla, pero
   modifica un fichero de un paquete Debian que se sobrescribiría con cada actualización.

## Decisión

Se aplican **la 1 y la 2** (Juan José, 4-nov), solo en el camino por defecto
(initramfs-tools), con ficheros propios en `config/includes.chroot/`:

- `etc/initramfs-tools/scripts/local-top/nimbo-aviso-ram`: corre antes que `cryptroot`
  (que declara como prerrequisito a todo `local-top`). Reutiliza `/lib/cryptsetup/functions`
  para resolver el disco y solo avisa.
- `etc/initramfs-tools/hooks/nimbo-cryptsetup-honesto` + `usr/lib/nimbo/initramfs/cryptsetup-envoltorio`:
  después del hook `cryptroot` de Debian, el binario pasa a `cryptsetup.real` y el envoltorio
  ocupa su lugar. Con 3 o 137 explica en español que el problema es la memoria, no la
  contraseña. **Devuelve siempre el mismo código**, así que el comportamiento de `cryptroot`
  no cambia.

No se parchea `cryptroot` (se descarta la opción 3).

## Consecuencias

- La persona ve la causa real, en español, antes y después de teclear. Verificado en QEMU
  con 1024/1280 MiB (fallan, con avisos) y 1536/2048 MiB (abren, sin avisos):
  `security/luks-tpm/evidencia/2026-11-04-h002-mensajes.md`.
- El mensaje engañoso de Debian sigue saliendo debajo del nuestro.
- Cambia el SHA de la ISO: entran tres ficheros al squashfs y, si el hook `cryptroot` mete
  cryptsetup en el initrd del live, también cambia ese initrd (por comprobar en el build).
  Hace falta la compuerta MATCH ×2.
- No cubre dracut (tras `nimbo-tpm-setup`, ADR-008).
- ~~Queda abierto (H-002): RAM mínima, E o A.~~ Resuelto el 8-nov, ver abajo.

## Ampliación (8-nov): RAM mínima declarada — decisión E

Medido (`security/luks-tpm/evidencia/2026-11-08-h002-ram-minima.md`): instalando **en la
propia máquina**, cryptsetup calibra argon2id con la RAM de esa máquina. Con 1536 MiB eligió
~307 MiB y con 1024 MiB ~438 MiB; en los dos casos el desbloqueo funcionó a la primera y sin
aviso. Lo único que impedía instalar con 1 GiB era el requisito de Calamares
(`requiredRam: 1.0`): una máquina de 1 GiB le muestra ~0.79 GiB.

**Decisión (Juan José, 8-nov):** **E** — RAM mínima declarada: **1 GiB nominal**, instalando en
la propia máquina. `welcome.conf` pasa a `requiredRam: 0.75` (el valor probado). La opción A
(limitar argon2id en el instalador) no hace falta. D (pbkdf2) sigue descartada.

- Riesgo que queda: mover el disco a un equipo con menos RAM que el instalador. Lo cubren los
  mensajes de este ADR.
- Test: `iso/live-build/tests/test-requisitos-calamares.sh` (CI) falla si `requiredRam`
  vuelve a rechazar un equipo de 1 GiB.
- Pendiente: confirmarlo en hardware real (guion `docs/manuales/verificacion-hardware-real.md`).

## Fecha

2026-11-04 · ampliado 2026-11-08
