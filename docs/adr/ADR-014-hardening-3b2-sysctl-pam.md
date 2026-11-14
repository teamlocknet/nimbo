# ADR-014 — Hardening fino 3B.2: parámetros del kernel (sysctl) y autenticación (PAM)

**Estado:** Aceptado (11-nov, Juan José, checkpoint en #63) · **Autor:** Emmanuel ·
**Integración a la ISO:** checkpoint de Juan José

## Contexto

RF-CORE-04 (Alta) pide un sistema "endurecido: actualizaciones automáticas deshabilitadas,
parámetros del kernel (sysctl) y autenticación (PAM) configurados de forma restrictiva", y
como criterio: *"La verificación automatizada confirma cada ajuste en la ISO y en el
sistema instalado."* (HU-04 CA-1/CA-2/CA-3).

- 3B.1 (hook `0100-nimbo-hermetismo`, Juan José) ya **deshabilitó las actualizaciones
  automáticas**. No había una verificación reutilizable de eso (cotejo, G3).
- sysctl y PAM siguen en los valores por defecto de Debian.
- Restricciones: no romper las herramientas de auditoría ni el navegador (ADR-012); **no
  dejar a nadie sin poder entrar**; RF-CORE-03 pide que el instalador **sugiera** contraseñas
  fuertes **sin obligarlas**; todo de bookworm `main` y reproducible.

## Opciones

| Opción | A favor | En contra |
|---|---|---|
| A. Nada más (valores de Debian) | Cero riesgo | No cumple RF-CORE-04 |
| **B. Lista corta y justificada de sysctl + `pam_faillock`, con verificador** | Cada ajuste se mide; bajo riesgo de romper cosas | Hay que mantener la lista |
| C. Perfil completo (CIS / KSPP entero, `pam_pwquality`, `userns` desactivado) | Más puntos en `lynis` | `pam_pwquality` **obliga** contraseñas (choca con RF-CORE-03); quitar `userns` debilita el sandbox de Firefox; más riesgo de romper herramientas |

## Decisión (aceptada el 11-nov): B

**sysctl** (`security/hardening/3b2/sysctl/99-zz-nimbo-hardening.conf` → `/etc/sysctl.d/`):

| Grupo | Parámetros | Por qué |
|---|---|---|
| Información del kernel | `kptr_restrict=2`, `dmesg_restrict=1`, `perf_event_paranoid=3` | No dar direcciones del kernel ni su log a usuarios sin privilegios |
| BPF y kexec | `unprivileged_bpf_disabled=1`, `bpf_jit_harden=2`, `kexec_load_disabled=1` | Superficie de explotación del kernel; `tcpdump` como root sigue funcionando |
| Procesos | `yama.ptrace_scope=1`, `suid_dumpable=0`, `dev.tty.ldisc_autoload=0` | Un proceso no espía a otro que no sea su hijo (root sí puede depurar) |
| Ficheros | `protected_symlinks/hardlinks=1`, `protected_fifos/regular=2` | Ataques por enlaces y ficheros en directorios compartidos |
| Red IPv4/IPv6 | sin redirecciones ni *source route*, `rp_filter=1`, `log_martians=1`, `tcp_syncookies=1`… | El equipo no es un router; evita desvíos de tráfico en la red del cliente |

**Excluidos a propósito:** `kernel.unprivileged_userns_clone=0` (Firefox usa espacios de
nombres para su sandbox: quitarlos lo **debilita**) y `accept_ra=0` en IPv6 (rompería la
red bajo demanda).

**PAM:** `pam_faillock` mediante perfiles de `pam-auth-update` (la vía de Debian, sin
editar `common-auth` a mano): 5 fallos en 15 min bloquean la cuenta 10 min; **root no se
bloquea** (recuperación). **No** se activa `pam_pwquality`: obligaría contraseñas fuertes,
y RF-CORE-03 pide solo sugerirlas.

*Corrección de la revisión de #47:* `pam-auth-update` convierte el `success=end` de
`pam_unix` en un salto al final del bloque Primary, así que una línea `authsucc` colocada
después nunca se ejecuta y el contador no se pone a cero tras un acierto (3 fallos →
acierto → 2 fallos = bloqueo). Por eso el perfil queda así:
- `auth`: `requisite pam_faillock.so preauth` (antes de `pam_unix`) y
  `[default=die] pam_faillock.so authfail` (después). **Sin `authsucc`.**
- `account`: `required pam_faillock.so` en el bloque **Additional**, que va después del salto
  de `pam_unix` y se ejecuta siempre tras un acierto. Es la fase que limpia el registro. (En
  el bloque Primary volvería a saltarse.)
- `faillock.conf` **sin `silent`**: la persona ve que la cuenta está bloqueada, en vez de creer
  que olvidó la contraseña (mensajes honestos, como ADR-009).

**Verificación:** `verify-hardening.sh`, un único script para live e instalado que comprueba
actualizaciones automáticas (sin cambiarlas), cada sysctl de la lista y PAM.

## Cómo se verifica

| Qué | Prueba | Pasa si |
|---|---|---|
| El verificador detecta cada ajuste roto | `pruebas/test-verify-hardening.sh` (raíz falsa, sin root). Rojo: 9/9 MAL sin verificador; después, 5 MAL con los casos de #47 | 13/13 casos OK |
| Medición antes/después | `aplicar-en-vm.sh` en una VM bookworm: `lynis` y `verify-hardening` antes y después | ✅ 11-nov: lynis 64 → 70; solo quedan los 3 fallos de actualizaciones, que en la ISO cierra 3B.1 (`0 fallos` se comprobará en la ISO) |
| No rompe herramientas | La misma ejecución: `tcpdump` en `lo`, `ping` sin root, `nimbo-audit --help`, `firefox-esr` | Todas funcionan |
| No deja sin acceso | En la VM: **3 fallos → acierto → 2 fallos** (no debe bloquear); 5 fallos seguidos → bloqueo con el mensaje visible; `faillock --reset` | ✅ 11-nov: 3 → 0 → 2, bloqueo a los 5 con mensaje, desbloqueo. Evidencia: `security/hardening/3b2/evidencia/2026-11-11-vm-3b2.md` |
| RF-CORE-04 CA-1/CA-2 | `verify-hardening.sh` en la ISO live y en el sistema instalado (QEMU, Juan José) | 0 fallos en ambos |
| No empeora el resto | MATCH ×2 · hermetismo 0/0 · RAM < 500 MB | Sin cambios |

## Consecuencias

- **`rp_filter = 1` frente a WireGuard (`nimbo-net`):** con túnel completo y rutas por
  *fwmark*, el modo estricto puede descartar tráfico legítimo. Se mide con Alejandro cuando
  exista `nimbo-net`. Si choca, `rp_filter = 2` (modo flexible) conserva casi todo el beneficio.
- `aplicar-en-vm.sh` instala `lynis` con red solo en la VM de prueba; `lynis` **nunca** entra
  en la receta de la ISO.

- **Gana:** RF-CORE-04 con una verificación automatizada reutilizable que además cubre lo de
  3B.1, y pruebas que demuestran que detecta cada ajuste roto.
- **Paga:** `ptrace_scope=1` impide que un usuario sin privilegios conecte un depurador a un
  proceso que no sea suyo (con `sudo` sí funciona). `faillock` puede bloquear 10 min a quien
  se equivoque 5 veces.
- **Integración:** copiar los ficheros a la receta (`includes.chroot` + `pam-auth-update` en
  un hook) cambia el SHA y toca `iso/live-build/`: **checkpoint de Juan José**, en un PR aparte.
- **Abierto:** `--firmware-chroot` (3B.2 de Juan José, maestro §0) queda fuera de este ADR.

## Pendiente tras la aceptación

Se cumplieron las condiciones de #47 con #60 (fase `account`, sin `authsucc` ni `silent`) y la
evidencia de #63 (`security/hardening/3b2/evidencia/2026-11-11-vm-3b2.md`). Quedan abiertos, y
no bloquean la aceptación:

- **RF-CORE-04 CA-1/CA-2 en la ISO integrada:** `verify-hardening` con **0 fallos** en la sesión
  live y en el sistema instalado (en la VM quedaron los 3 de actualizaciones automáticas, que en
  la ISO cierra 3B.1).
- **faillock con un `login` real** en QEMU sobre la ISO integrada. En la VM, el "acierto" se hizo
  con `sudo -n true` (fase `account`). El primer intento en la consola tty3 no dejó **ningún**
  `FAILED LOGIN` en el diario, así que no llegó a hacerse ningún intento en esa consola (el
  diario los registra aunque el contador se ponga a cero); se repetirá en la integración.
- **`rp_filter = 1` frente a WireGuard** (`nimbo-net`, ADR-011): medir cuando se pruebe el túnel.
  Si choca, `rp_filter = 2`.

## Fecha

2026-11-09 (propuesto) · 2026-11-11 (aceptado)
