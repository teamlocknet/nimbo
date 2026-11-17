# Endurecimiento del sistema (3B.2) — RF-CORE-04

## Qué hace

- **33 parámetros del kernel** (sysctl): ocultan información del kernel, cierran BPF y kexec,
  protegen procesos y enlaces, y no aceptan desvíos de tráfico de la red del cliente.
- **Bloqueo por intentos fallidos** (`pam_faillock`): 5 contraseñas mal en 15 min bloquean la
  cuenta 10 min, **y la persona lo ve** ("la cuenta está bloqueada"). root no se bloquea.
- **Contraseñas fuertes: se sugieren, no se obligan** (RF-CORE-03): por eso no hay `pam_pwquality`.
- **`verify-hardening`:** un único script que confirma cada ajuste en la ISO live y en el
  sistema instalado, incluidas las actualizaciones automáticas cerradas por 3B.1.

**Lo que se dejó fuera a propósito:** quitar los espacios de nombres de usuario (debilitaría el
sandbox de Firefox) y la autoconfiguración IPv6 (rompería la red a demanda).

## Cómo se prueba

| Qué | Prueba |
|---|---|
| El verificador detecta cada ajuste roto | Raíz falsa, sin root: **14/14 casos** (cada ajuste roto debe dar FALLO con su nombre) |
| Aplicación real | `aplicar-en-vm.sh`: lynis y verificador antes y después, y que las herramientas sigan funcionando |
| Bloqueo de cuenta | `su` con clave mala, leyendo el contador sin `sudo` |

## Qué se midió (VM Debian 12, 11-nov)

| | Antes | Después |
|---|---|---|
| Índice de lynis | 64 | **70** |
| Fallos de `verify-hardening` (de 44) | 29 | **3** (los de actualizaciones, que en la ISO cierra 3B.1) |
| Herramientas (`tcpdump`, `ping`, Firefox) | — | funcionan |

**Bloqueo de cuenta:** 3 fallos → un acierto → **contador a 0** → 2 fallos (**no bloquea**) →
5 fallos seguidos → *"La cuenta está bloqueada debido a 5 inicios de sesión fallidos"*.

## Hallazgos

1. **`authsucc` nunca se ejecutaba** con `pam-auth-update` (lo vio Juan José en la revisión): el
   contador no se ponía a cero tras un acierto. Se movió a la fase `account`, en el bloque
   *Additional*, y la VM confirma 3 → 0.
2. **`procps` pisaba un parámetro:** su `99-protect-links.conf` se aplicaba después del nuestro y
   dejaba `fs.protected_fifos` en 1. Nuestro fichero pasa a `99-zz-…` y una prueba lo exige.
3. **Medir puede cambiar lo medido:** un `sudo` como el mismo usuario es un acierto y vacía el
   contador; leerlo con `sudo` daba siempre 0. Se lee sin `sudo`.

## Sobre la ISO integrada

`verify-hardening`: **0 fallos de 44** en el live y en el instalado (Juan José, #83,
`repro/evidencia/2026-11-12-qemu-pr83.md`), otra vez en el instalado sin red (RNF-03, 16-nov) y
en las dos instalaciones de la prueba de `nimbo-net` (Alejandro, #84). Los 3 fallos de la VM
(actualizaciones automáticas) los cierra 3B.1 en la ISO, como se esperaba.

**Bloqueo de cuenta con inicio de sesión real en la ISO** (16-nov, #99): 3 fallos → 0 con un
`login` real correcto → 5 fallos → "The account is locked due to 5 failed logins" → a los 10
minutos entra de nuevo. Salieron dos cosas para el manual: con la cuenta bloqueada `login` ya
no pide contraseña (lo que se escriba se ve en pantalla) y `sudo` falla sin decir que está
bloqueada.

**`rp_filter` frente a WireGuard:** `rp_filter=1` en `all`, `default`, `enp0s3` y `wg-nimbo` con
el túnel de `nimbo-net` activo, en las dos instalaciones de la ISO (Alejandro, #84): el modo
estricto no rompe la red del equipo.

## Lo que falta

Nada de RF-CORE-04. ADR-014 pasa a Aceptado con los tres pendientes verificados (#69).

*Evidencia:* `security/hardening/3b2/evidencia/2026-11-11-vm-3b2.md` · *Diseño:* ADR-014 ·
*Manual:* `docs/manuales/endurecimiento-3b2.md`
