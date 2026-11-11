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

## Lo que falta

`verify-hardening` en la **ISO integrada** (live e instalada) con 0 fallos, y medir `rp_filter`
frente a WireGuard cuando exista `nimbo-net`.

*Evidencia:* `security/hardening/3b2/evidencia/2026-11-11-vm-3b2.md` · *Diseño:* ADR-014 ·
*Manual:* `docs/manuales/endurecimiento-3b2.md`
