# Manual — Navegación segura (nimbo-nav)

**Requisitos:** RF-NAV-01 (navegador endurecido) y RF-NAV-02 (Tor con detección de fugas).
**Diseño:** [ADR-012](../adr/ADR-012-navegacion-segura-tor.md). **Código:**
[`packages/nimbo-nav`](../../packages/nimbo-nav/README.md). **Responsable:** Emmanuel.

## Qué hace

- **Navegador normal endurecido.** `firefox-esr` de Debian con políticas bloqueadas: sin
  telemetría, estudios, Pocket, cuentas de Firefox, DNS sobre HTTPS, detección de portal
  cautivo, sugerencias de búsqueda, Safe Browsing, notificaciones push ni descargas
  automáticas de complementos. Al abrirlo y dejarlo quieto **no debe conectarse a nada**.
- **Modo Tor a petición.** Tor **no arranca solo**: en reposo nimbo sigue sin conexiones ni
  puertos abiertos. Al activarlo, una tabla de cortafuegos deja salir **solo al proceso
  tor**. Si cualquier otro programa intenta salir, el paquete se bloquea y se cuenta.
- **Detección de fugas.** `nimbo-leakcheck` junta el contador de esa tabla con las
  conexiones abiertas, y avisa en el escritorio si algo intentó salir fuera de Tor.

## Cómo se usa

| Quiero… | Comando |
|---|---|
| Navegar normal (sin Tor) | Menú → Firefox, o `firefox-esr` |
| Levantar la red por cable (sin red no hay Tor) | `sudo nimbo-red on` |
| Activar el modo Tor | `nimbo-tor on` (el sistema pide tu contraseña) |
| Navegar por Tor | Menú → "Navegar por Tor", o `nimbo-navegar-tor` |
| Comprobar que no hay fugas | `sudo nimbo-leakcheck` → `0` sin fugas · `1` FUGA · `2` modo apagado · `3` no se pudo comprobar |
| Ver los paquetes bloqueados | `sudo journalctl -k \| grep nimbo-fuga` |
| Saber si el modo está activo | `nimbo-tor estado` |
| Apagar el modo Tor | `nimbo-tor off` |
| Soltar la red | `sudo nimbo-red off` |

**Mientras el modo Tor está activo, solo Tor sale a la red**: el navegador normal y
cualquier otro programa se quedan sin red. Es a propósito.

## Lo que NO hace (límites declarados)

- **Evita fugas de red; no protege frente a la huella del navegador.** El perfil Tor no es
  Tor Browser: lleva `resistFingerprinting` y `letterboxing`, que reducen la diferencia pero
  no la eliminan.
- **OCSP apagado en el perfil Tor** (`security.OCSP.enabled = 0`): el navegador no consulta
  si un certificado fue revocado, para no hacer peticiones fuera de la navegación. Es una
  contrapartida aceptada: un certificado revocado pero aún válido no se detectaría.
- **El aviso falla hacia la alerta:** si el vigilante de fugas se detiene, da error o deja de
  actualizarse, el navegador avisa igual que ante una fuga. Nunca se toma por "limpio".
- Solo red por cable (ADR-019). Wi-Fi queda fuera de v1.
- **El modo Tor y la red del equipo (`nimbo-net`) no pueden estar activos a la vez en v1:**
  `nimbo-tor on` se niega si hay un túnel de `nimbo-net` (primero, `nimbo-net leave`).
- Si el modo Tor no llega a arrancar, systemd deshace lo que alcanzó a hacer y
  `nimbo-tor estado` dice "falló". `nimbo-tor off` solo dice "red restaurada" cuando la
  unidad quedó realmente apagada.
- El navegador queda en la versión del snapshot de la ISO (`firefox-esr`
  140.14.0esr-1~deb12u1, publicada el 21-ago-2026) y no se actualiza solo (ADR-012).

## Cómo se verificó

| Requisito | Prueba | Resultado |
|---|---|---|
| Configuración (RF-NAV-01 CA-2) y lógica de detección (RF-NAV-02 CA-3) | 31 pruebas unitarias (`python3 -m pytest` en `packages/nimbo-nav`), escritas antes que el código | Rojo: 8 failed + 4 errors → verde: 31 passed |
| RF-NAV-01 CA-1: 0 conexiones en reposo | `pruebas/prueba-reposo-navegador.sh` en una VM (pcap de 120 s) | *Pendiente: medir en la VM* |
| RF-NAV-02 CA-1/CA-2: 0 DNS y 0 paquetes fuera del túnel | `pruebas/prueba-fugas-tor.sh` en una VM | *Pendiente: medir en la VM* |
| RF-NAV-02 CA-3: la fuga provocada se detecta | La misma prueba, parte negativa (`curl` directo) | *Pendiente: medir en la VM* |
| RNF-01 y RNF-02 no empeoran | `verify-hermetismo-in-qemu.sh` y `measure-ram-in-qemu.sh` sobre la ISO integrada | *Pendiente: integración a la ISO* |

Las filas pendientes se completan con el `informe.md` que deja cada prueba (comando y salida).
