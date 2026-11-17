# Evidencia — `pam_faillock` con inicios de sesión reales en la ISO instalada (16-nov-2026)

**Quién:** Emmanuel, con Claude Code manejando la VM. La contraseña real la tecleó Emmanuel; los
fallos se hicieron con una contraseña **inventada y errónea** (`claveMal123`), que no es la de
nadie. **Resultado:** cuenta, se pone a cero con un inicio de sesión real y bloquea a los 5
fallos con un mensaje visible; a los 10 minutos se desbloquea sola. Cierra el pendiente de ADR-014 ("faillock con un `login` real";
en la VM del 11-nov el acierto se hizo con `sudo -n true`).

## Entorno

- ISO de `main` `eb3bc36` (`b0df8d62…`, MATCH ×2), instalada con Calamares cifrado en VirtualBox
  (VM `nimbo-iso-nav`, instantánea `antes-faillock`). Es la misma instalación de
  `packages/nimbo-nav/evidencia/2026-11-16-iso-rf-nav.md`.
- Configuración de la ISO: `deny = 5`, `fail_interval = 900`, `unlock_time = 600`, sin `silent`
  ni `even_deny_root` (`security/hardening/3b2/pam/faillock.conf`).
- Intentos en la consola `tty3` (`login` de verdad, no `su`). Un registro en la sesión gráfica
  anotaba cada 2 s el número de entradas de `/usr/sbin/faillock --user emmanuel` (leído **sin
  `sudo`**, que contaría como acierto y pondría el contador a cero).

## Resultados

| Hora (UTC, VM) | Acción | Contador |
|---|---|---|
| 01:17:25 | inicio | 0 |
| 01:17:45 · 01:17:53 · 01:18:03 | 3 × `login` con clave mala → "Login incorrect" | 1 · 2 · 3 |
| 01:21:31 | **`login` real con la contraseña correcta** (Emmanuel) | **0** |
| 01:22:40 … 01:23:16 | 5 × `login` con clave mala | 1 · 2 · 3 · 4 · **5** |
| siguiente intento | al escribir solo el usuario: **"The account is locked due to 5 failed logins. (10 minutes left to unlock)"** y vuelve a `nimbo login:` | 5 |
| 01:35:49 (12 min después del bloqueo) | **`login` real con la contraseña correcta**: entra (pide `Password:` de nuevo) | **0** |

`faillock` lista las 5 entradas como válidas (`V`); tras el desbloqueo, ninguna.

Capturas: [3 fallos](2026-11-16-iso-faillock/1-tres-fallos.png) ·
[acierto y contador a 0](2026-11-16-iso-faillock/2-acierto-contador-0.png) ·
[cuenta bloqueada](2026-11-16-iso-faillock/3-cuenta-bloqueada.png) ·
[`sudo` con la cuenta bloqueada](2026-11-16-iso-faillock/4-sudo-bloqueado.png) ·
[desbloqueo automático](2026-11-16-iso-faillock/5-desbloqueo-automatico.png). El primer intento de Emmanuel antes del
acierto dio "Login incorrect" sin sumar al contador: la pantalla de `login` había caducado.

## Observaciones (no son fallos de nimbo; van al manual)

1. **Con la cuenta bloqueada, `login` no pide contraseña.** `pam_faillock` rechaza en la fase
   previa (`preauth`) y `login` vuelve a pedir el usuario. Lo que se escriba a continuación cae
   en el campo de usuario **y se ve en pantalla**: quien teclee su contraseña de memoria la
   deja a la vista. Es el comportamiento normal de `preauth`, que es lo que hace cumplir el
   bloqueo; cambiarlo sería tocar PAM (checkpoint). Se avisa en el manual: si ves el mensaje
   de bloqueo, no escribas la contraseña.
2. **`sudo` con la cuenta bloqueada no lo explica.** `sudo -v` falla tres veces sin pedir la
   contraseña ("Lo siento, pruebe otra vez." ×2, `sudo: 3 incorrect password attempts`,
   código 1) y no dice que la cuenta está bloqueada. El contador sigue en 5 (el bloqueo no se
   alarga). Una cuenta bloqueada no puede usar `sudo` para desbloquearse: hay que esperar los
   10 minutos o que otra cuenta administradora haga `sudo faillock --user <usuario> --reset`.
   Se corrige el manual, que daba esos comandos sin esa aclaración.
