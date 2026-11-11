# ADR-012 — Navegación segura: navegador endurecido y Tor con detección de fugas

**Estado:** Aceptado (10-nov, Juan José, checkpoint en #45) · **Autor:** Emmanuel

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
- La base hoy **no trae** navegador ni `tor` ni NetworkManager. **`nftables` sí está en la ISO**
  (1.0.6-2+deb12u2, en `live-image-amd64.packages`) con `nftables.service` deshabilitado: lo
  nuevo es la tabla de nimbo, no el paquete. *(Errata de la versión Propuesta, que decía que
  no lo traía.)*
- La red tampoco se levanta sola: no hay ninguna interfaz configurada. La levanta a demanda
  `sudo nimbo-red on` (ADR-019).

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
| **D2. Configuración del navegador + cortafuegos que falla cerrado en modo Tor + contador** | Con `nftables`: en modo Tor solo puede salir el usuario `debian-tor` (más loopback); cualquier otro paquete saliente **se descarta y se cuenta**. El contador es el detector: si sube, `nimbo-leakcheck` avisa | Toca la red del sistema (la tabla, no el paquete, que ya está): **es núcleo (checkpoint)** |

## Decisión (aceptada el 10-nov con las condiciones de #45)

1. **A1:** `firefox-esr` de bookworm, endurecido con `policies.json` (bloqueado) y preferencias
   del sistema. La lista inicial está abajo; `arkenfox/user.js` sirve **solo de referencia** de qué
   revisar, no se copia.
2. **B1 + C1:** `tor` de bookworm, con el servicio **deshabilitado por defecto**.
   El modo Tor lo arranca y lo para **una unidad systemd propia, `nimbo-modo-tor.service`**:
   al arrancar, **tabla → tor → vigilante**; al parar, en orden inverso (vigilante → tor →
   tabla). `nimbo-tor on/off` solo arranca o para esa unidad: no hay scripts con `sudo`
   sueltos ni un CLI entero corriendo como root. La red la levanta antes `nimbo-red on`
   (ADR-019); `nimbo-tor` no la configura. El navegador abre un **perfil Tor** separado (SOCKS5
   `127.0.0.1:9050`, `network.proxy.socks_remote_dns = true`, WebRTC apagado, sin prefetch ni
   especulación, `privacy.resistFingerprinting = true` y
   `privacy.resistFingerprinting.letterboxing = true`). El listener 9050 es **solo loopback** y
   solo existe mientras el modo está activo.
   **Nombre y textos:** el lanzador se llama "Navegar por Tor"; ni el lanzador ni el manual dicen
   "Tor Browser" ni "anónimo". El límite se dice siempre igual: *"evita fugas de red; no protege
   frente a la huella del navegador"*. Contrapartida declarada: en el perfil Tor el OCSP queda
   apagado (`security.OCSP.enabled = 0`), para no hacer peticiones de revocación fuera de la
   navegación.
3. **D2:** en modo Tor, una tabla `nftables` propia de nimbo permite solo `lo` y el UID
   `debian-tor`; el resto se descarta con contador. `nimbo-leakcheck` lee el contador y las
   consultas DNS. Si encuentra algo, **avisa** (notificación en el escritorio y código de salida
   distinto de 0) y lo deja en un registro. Mientras el modo Tor está activo, **nada más sale a
   la red**, incluido el navegador normal. Fuera del modo Tor, la tabla no existe y
   `nftables.service` sigue deshabilitado. La tabla vive en su propio espacio
   (`table inet nimbo_tor`) y **nunca** usa `flush ruleset`, para no pisar las reglas de
   `nimbo-net` (WireGuard). En IPv6 se descarta todo el saliente que no sea link-local.
   Cualquier cambio a la tabla o a la unidad es checkpoint de Juan José.
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
- **Paga:** `firefox-esr` y `tor` hacen crecer la ISO (`nftables` ya está). Instalados ocupan
  unos 272 MiB y 5.7 MiB respectivamente (`Installed-Size` del snapshot, antes de la
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
  navegador es lo más expuesto. **Decidido (#45):** (1) para v1 se acepta y se declara en el
  manual y en la sustentación, con la versión y la fecha; (2) subir `NIMBO_SNAPSHOT` antes
  del release v1.0 se decide en la revisión de alcance #2 del 16-nov (checkpoint de receta).
  No hace falta anclar `debian-security` aparte: ya está anclado. Las actualizaciones
  posteriores en campo van por `nimbo-update-offline` (ADR-013).
- **Límite honesto (aceptado en #45):** el perfil Tor de Firefox **no** es Tor Browser. Texto
  fijo para el lanzador, el manual y la sustentación: *"evita fugas de red; no protege frente
  a la huella del navegador"*. `resistFingerprinting` y `letterboxing` reducen la brecha, pero
  no la cierran.
- **Checkpoints:** integrar los paquetes a la ISO (cambia el SHA) y cualquier cambio a la tabla
  `nftables` o a `nimbo-modo-tor.service` esperan el OK de Juan José.
- **Red (resuelto en #45 → ADR-019):** sin NetworkManager y offline por defecto. La red por cable
  la levanta `sudo nimbo-red on` y la suelta `sudo nimbo-red off`. **Wi-Fi queda fuera de v1.**
  El modo Tor da por hecho que la red ya está levantada.

## Fecha

2026-11-09 (propuesto) · 2026-11-10 (aceptado)
