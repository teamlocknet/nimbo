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
| Activar el modo Tor | `sudo nimbo-tor on` |
| Navegar por Tor | Menú → "Navegar por Tor (nimbo)", o `nimbo-navegar-tor` |
| Comprobar que no hay fugas | `sudo nimbo-leakcheck` → `0` sin fugas · `1` FUGA · `2` modo apagado |
| Ver los paquetes bloqueados | `sudo journalctl -k \| grep nimbo-fuga` |
| Saber si el modo está activo | `sudo nimbo-tor estado` |
| Volver a la red normal | `sudo nimbo-tor off` |

**Mientras el modo Tor está activo, solo Tor sale a la red**: el navegador normal y
cualquier otro programa se quedan sin red. Es a propósito.

## Lo que NO hace (límites declarados)

- El perfil Tor de Firefox **no es Tor Browser**: evita fugas de red, pero no iguala la
  protección de Tor Browser contra la identificación del navegador (*fingerprinting*).
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
