# ADR-012 — Navegación segura: navegador endurecido y Tor con detección de fugas

**Estado:** Propuesto (9-nov, Emmanuel) · **Valida:** Juan José, antes de implementar

## Contexto

Requisitos de prioridad Alta (D15 = B):

- **RF-NAV-01 / HU-07:** navegador con privacidad endurecida y sin telemetría. *"El navegador no
  genera conexiones no solicitadas al abrirse en reposo."* CA-2: telemetría y reportes
  automáticos desactivados.
- **RF-NAV-02 / HU-08:** navegar por Tor y detectar fugas de DNS o de tráfico fuera del túnel.
  CA-2: *cero fugas de DNS y cero paquetes fuera del túnel*. CA-3: si hay una fuga, el
  sistema **avisa al usuario**.

Restricciones del proyecto (no negociables):

- **Hermetismo en reposo (RNF-01):** 0 sospechosos y 0 listeners no-loopback, con el criterio de
  `iso/live-build/verify-hermetismo-in-qemu.sh`. Nada puede arrancar solo y salir a la red.
- **Reproducible y offline:** solo paquetes de bookworm `main` del snapshot anclado (o un `.deb`
  propio). Nada se descarga en tiempo de ejecución.
- **RAM < 500 MB en reposo** (se mide con el escritorio cargado y el navegador cerrado).
- La base hoy **no trae** navegador, `tor`, `nftables` ni NetworkManager (listas de paquetes
  de `iso/live-build/config/package-lists/`).

## Opciones

**A. Navegador**

| Opción | A favor | En contra |
|---|---|---|
| **A1. `firefox-esr` (bookworm)** | Políticas empresariales (`policies.json`) documentadas y bloqueables, que cubren telemetría, estudios, Pocket, cuentas, DoH, portal cautivo y actualizaciones · un fichero de preferencias del sistema para lo que no cubren las políticas · el proxy SOCKS con DNS remoto **no cae a conexión directa** si Tor no está | Por defecto hace muchas conexiones al arrancar (Remote Settings, Safe Browsing, push, detección de portal, sugerencias); hay que cerrarlas una a una y **medirlas** |
| A2. `chromium` (bookworm) | Políticas también disponibles | Menos control sobre las conexiones de arranque (servicios de componentes, variaciones) · más RAM y más tamaño de ISO · el proxy y el DNS remoto se configuran con menos garantías |

**B. Tor**

| Opción | A favor | En contra |
|---|---|---|
| **B1. Paquete `tor` de bookworm + el mismo Firefox con un perfil "Tor"** | Viene del snapshot (reproducible); sin descargas | **No es Tor Browser:** no iguala su resistencia al *fingerprinting*. Se dice así, sin maquillarlo |
| B2. `torbrowser-launcher` | Tor Browser real | **Descarga el navegador en tiempo de ejecución:** rompe el modo offline, la reproducibilidad y el hermetismo. **Descartado** |
| B3. Tor Browser empaquetado por nosotros | Tor Browser real | Binario de terceros fuera de Debian, firmas y actualizaciones a mano: no cabe en el calendario. Queda fuera de v1 |

**C. ¿Tor arranca solo?**

| Opción | Consecuencia |
|---|---|
| **C1. Desactivado; lo enciende el usuario** (`nimbo-tor on/off`) | El hermetismo en reposo no cambia (0/0) |
| C2. Activo al arrancar | Conexiones a los directorios de Tor en reposo: **rompe RNF-01**. Descartado |

**D. Cómo se evitan y se detectan las fugas**

| Opción | A favor | En contra |
|---|---|---|
| D1. Solo la configuración del navegador (proxy SOCKS con DNS remoto) | Simple | Si un ajuste falla, nadie lo nota; no cubre otros procesos |
| **D2. Configuración del navegador + cortafuegos que falla cerrado en modo Tor + contador** | Con `nftables`: en modo Tor solo puede salir el usuario `debian-tor` (más loopback); cualquier otro paquete saliente **se descarta y se cuenta**. El contador es el detector: si sube, `nimbo-leakcheck` avisa | Añade `nftables` a la ISO y toca la red del sistema: **es núcleo (checkpoint)** |

## Decisión (propuesta)

1. **A1:** `firefox-esr` de bookworm, endurecido con `policies.json` (bloqueado) y preferencias
   del sistema. La lista inicial está abajo; `arkenfox/user.js` sirve **solo de referencia** de qué
   revisar, no se copia.
2. **B1 + C1:** `tor` de bookworm, con el servicio **deshabilitado por defecto**.
   `nimbo-tor on` lo arranca y abre Firefox con un **perfil Tor** separado (SOCKS5
   `127.0.0.1:9050`, `network.proxy.socks_remote_dns = true`, WebRTC apagado, sin prefetch ni
   especulación). `nimbo-tor off` lo para. El listener 9050 es **solo loopback** y solo existe
   mientras el modo está activo.
3. **D2:** en modo Tor, una tabla `nftables` propia de nimbo permite solo `lo` y el UID
   `debian-tor`; el resto se descarta con contador. `nimbo-leakcheck` lee el contador y las
   consultas DNS. Si encuentra algo, **avisa** (notificación en el escritorio y código de salida
   distinto de 0) y lo deja en un registro. Mientras el modo Tor está activo, **nada más sale a
   la red**, incluido el navegador normal. Fuera del modo Tor, la tabla no existe.
   **Excepción explícita, sin contar como fuga** (observación de Juan José en #44): el tráfico
   de puesta en marcha de la NIC que ya admite el criterio de hermetismo, es decir, DHCPv4
   (UDP 68 → 67) y NDP/RS de IPv6 link-local (ICMPv6 hacia `ff02::/16` y `fe80::/10`). Sin
   esa excepción, la renovación de la concesión daría un falso positivo y, en una sesión más
   larga que la concesión, la máquina perdería la IP. ARP no pasa por la tabla `inet`.
4. **Qué es una fuga para nimbo** (con el modo Tor activo): (a) cualquier DNS (53/udp-tcp, DoH
   incluido) hacia fuera de loopback · (b) cualquier paquete saliente no-loopback de un proceso
   que no sea `tor` · (c) STUN/UDP de WebRTC · (d) IPv6 directo · (e) peticiones del navegador
   que se salten el proxy (OCSP, portal cautivo, prefetch).
5. **El navegador "normal"** (sin Tor) usa el mismo endurecimiento y **no** está forzado a Tor:
   RF-NAV-01 solo exige que no haga conexiones no solicitadas.

**Ajustes iniciales del navegador** (cada uno se verifica con el pcap en reposo, no se da por
bueno): `DisableTelemetry`, `DisableFirefoxStudies`, `DisablePocket`,
`DisableFirefoxAccounts`, `DisableFeedbackCommands`, `CaptivePortal: false`,
`NetworkPrediction: false`, `DNSOverHTTPS` desactivado y bloqueado, `ExtensionUpdate: false`,
`SearchSuggestEnabled: false`, `FirefoxHome` sin contenido patrocinado, página de inicio
`about:blank`; y en preferencias: Remote Settings, Safe Browsing, servicio push
(`dom.push.enabled`), detección de conectividad, región/geolocalización y Normandy apagados.
**Pendiente de medir:** qué rutas de política lee el `firefox-esr` del snapshot
(`/etc/firefox/policies/` o `/usr/lib/firefox-esr/distribution/`) y si Remote Settings se
puede apagar del todo sin romper el navegador.

## Cómo se verifica

| Requisito | Prueba (rojo primero) | Pasa si |
|---|---|---|
| RNF-01 (no empeora) | `verify-hermetismo-in-qemu.sh` sobre la ISO con navegación | 0 sospechosos, 0 listeners (Tor apagado) |
| RF-NAV-01 CA-1 | Firefox abierto en `about:blank`, **120 s** sin tocar, pcap en la VM. **Rojo:** Firefox sin políticas → sí aparecen conexiones | 0 DNS, 0 SYN, 0 paquetes web |
| RF-NAV-01 CA-2 | `about:policies` sin errores y un script que compara las preferencias bloqueadas | Todas las de la lista, activas |
| RF-NAV-02 CA-1/CA-2 | Modo Tor, visitar sitios de prueba, pcap en la interfaz externa. Comparar con las conexiones de `tor` (`ss -tnp`) | 0 DNS y 0 paquetes que no sean de `tor` hacia sus relés |
| RF-NAV-02 CA-3 | **Prueba negativa:** quitar el proxy del perfil Tor (o lanzar `curl` directo) | `nimbo-leakcheck` detecta la fuga, avisa y sale distinto de 0 |
| Sin falsos positivos (DHCP) | Modo Tor durante **más que la concesión DHCP** de la VM (concesión corta en la red de prueba). **Rojo:** la tabla sin la excepción → el contador sube y se pierde la IP | Contador de fugas en 0, sin aviso, y la IP se renueva |
| RNF-02 | `measure-ram-in-qemu.sh` | < 500 MB en reposo (navegador cerrado) |
| RNF-SEC-07 | Compuerta MATCH ×2 al integrar | Mismo SHA-256 |

Las pruebas de fugas necesitan red en la VM de prueba. Eso no contradice el hermetismo de la
ISO, que se mide aparte y sin red.

## Consecuencias

- **Gana:** RF-NAV-01 y RF-NAV-02 con evidencia medida. La protección falla cerrada: si Tor cae,
  el perfil Tor no navega en vez de salir directo, y el cortafuegos descarta lo que se escape.
- **Paga:** `firefox-esr` + `tor` + `nftables` hacen crecer la ISO. Instalados ocupan unos
  272 MiB, 5.7 MiB y 0.2 MiB respectivamente (`Installed-Size` del snapshot, antes de la
  compresión del squashfs); el crecimiento real de la ISO **se mide** al integrar. La RAM en
  reposo no debería cambiar porque nada arranca solo; se mide igual. Endurecer Firefox es
  trabajo de medir y ajustar, no de una sola vez.
- **Navegador congelado en el snapshot** (observación de Juan José en #44). La receta ancla
  `bookworm` **y** `bookworm-security` al mismo snapshot (`auto/config`,
  `--mirror-chroot-security`), así que entra la última versión de seguridad a esa fecha y
  después ninguna más. Con `NIMBO_SNAPSHOT=20260901T000000Z` (consultado en
  snapshot.debian.org el 9-nov):

  | Paquete | Versión que entra | Archivo | Publicada en Debian |
  |---|---|---|---|
  | `firefox-esr` | `140.14.0esr-1~deb12u1` | bookworm-security | 21-ago-2026 (`debian-security`) |
  | `tor` | `0.4.9.11-0+deb12u1` | bookworm y bookworm-security | — |
  | `nftables` | `1.0.6-2+deb12u2` | bookworm | — |

  Al 30-nov el navegador llevará unos tres meses sin parches. Afecta a todo el sistema, pero el
  navegador es lo más expuesto. **Propuesta:** (1) para v1, aceptarlo y declararlo en el
  manual y en la sustentación, con la versión y la fecha; (2) **subir `NIMBO_SNAPSHOT` antes
  del release v1.0** para que entre el último `firefox-esr` de `bookworm-security`. Lo segundo
  cambia el SHA de toda la ISO y es **checkpoint de receta**: lo decide Juan José. No hace
  falta anclar `debian-security` aparte: ya está anclado. Las actualizaciones posteriores en
  campo dependen de RF-UPD-01 (`nimbo-update-offline`, dueño por decidir).
- **Límite honesto:** el perfil Tor de Firefox **no** es Tor Browser: evita fugas de red, no el
  *fingerprinting*. Se dirá así en el manual y en la sustentación.
- **Checkpoints:** integrar los paquetes a la ISO (cambia el SHA) y la tabla `nftables` (red del
  sistema) esperan el OK de Juan José.
- **Abierto:** cómo se activa la red en la ISO (no hay NetworkManager) para navegar fuera de la
  VM de prueba: se resuelve con Juan José en el checkpoint de integración.

## Fecha

2026-11-09
