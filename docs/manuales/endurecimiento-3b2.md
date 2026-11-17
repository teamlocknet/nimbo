# Manual — Endurecimiento del sistema base (3B.2)

**Requisito:** RF-CORE-04 / HU-04. **Diseño:** [ADR-014](../adr/ADR-014-hardening-3b2-sysctl-pam.md).
**Código:** [`security/hardening/3b2`](../../security/hardening/3b2/README.md). **Responsable:** Emmanuel.

## Qué hace

- **Actualizaciones automáticas deshabilitadas.** Lo cerró 3B.1 (Juan José); aquí solo se
  verifica que sigue cerrado.
- **Parámetros del kernel restrictivos** (33, en `/etc/sysctl.d/99-zz-nimbo-hardening.conf`).
  Ocultan información del kernel a usuarios sin privilegios, cierran BPF y kexec, protegen
  procesos y enlaces de ficheros, y hacen que el equipo no acepte desvíos de tráfico de la
  red del cliente.
- **Bloqueo por intentos fallidos** (`pam_faillock`). 5 contraseñas erróneas en 15 minutos
  bloquean la cuenta 10 minutos, y el sistema **dice que la cuenta está bloqueada**. Un
  acierto pone el contador a cero. **root no se bloquea**, para poder recuperar el equipo.
- **Contraseñas:** el instalador sugiere contraseñas fuertes, pero **no las obliga**
  (RF-CORE-03). Por eso no se usa `pam_pwquality`.

## Cómo se usa

| Quiero… | Comando |
|---|---|
| Verificar todo el endurecimiento | `sudo /usr/lib/nimbo/verify-hardening` (0 = OK, 1 = algún fallo) |
| Ver tus intentos fallidos | `/usr/sbin/faillock --user <tu-usuario>` (**sin** `sudo`: `sudo` cuenta como acierto y pone el contador a cero) |
| Desbloquear una cuenta | esperar 10 minutos, o que **otra** cuenta administradora haga `sudo faillock --user <usuario> --reset` |
| Ver un parámetro | `sysctl kernel.kptr_restrict` |

## Efectos que conviene conocer

- Un usuario sin `sudo` no puede conectar un depurador a procesos que no sean hijos suyos
  (`ptrace_scope=1`). Con `sudo` sí.
- `dmesg` necesita `sudo`.
- Cualquier uso correcto de la cuenta, también `sudo`, pone el contador de fallos a cero.
- **Si ves "The account is locked due to 5 failed logins", no escribas tu contraseña.** Con la
  cuenta bloqueada el sistema ya no la pide y vuelve a preguntar el usuario: lo que escribas
  se vería en pantalla. Espera los minutos que indica.
- Una cuenta bloqueada **tampoco puede usar `sudo`**: falla sin pedir la contraseña ("3
  incorrect password attempts") y no dice que está bloqueada. No es que hayas olvidado la
  contraseña: espera a que pase el bloqueo.
- Se mantienen a propósito: los espacios de nombres de usuario (el sandbox de Firefox los
  necesita) y la autoconfiguración IPv6.

## Cómo se verificó

| Qué | Prueba | Resultado |
|---|---|---|
| El verificador detecta cada ajuste roto | `pruebas/test-verify-hardening.sh` (raíz falsa, sin root) | Rojo: 9 casos MAL → verde: 9/9 OK; con la revisión de #47: 5 MAL → 13/13 OK |
| Medición antes/después y herramientas | `aplicar-en-vm.sh` en una VM Debian 12 (lynis + verificador + tcpdump, ping, Firefox) | ✅ VM, 11-nov: lynis 64 → 70; fallos del verificador 29 → 3 (los 3 de actualizaciones, que cierra 3B.1 en la ISO); herramientas ok |
| Inicio de sesión y bloqueo | `su` con clave mala en la VM, leyendo el contador sin `sudo`: 3 fallos → acierto → 2 fallos no bloquea; 5 fallos bloquean | ✅ VM, 11-nov: 3 → 0 → 2; a los 5, "La cuenta está bloqueada debido a 5 inicios de sesión fallidos". ✅ **ISO instalada, 16-nov, con `login` real en consola:** 3 → 0 tras el acierto real → 5 → "The account is locked due to 5 failed logins" → a los 10 min entra de nuevo |
| RF-CORE-04 CA-1/CA-2 en la ISO live e instalada | `verify-hardening` en QEMU tras integrar | ✅ 0 fallos de 44 en live e instalado (Juan José, #83; otra vez sin red en RNF-03) |
