# Evidencia — ICMP de error del kernel a tráfico entrante contado como "fuga" (18/19-nov-2026)

**Quién:** Juan José, con Claude Code preparando el script (la sesión y `sudo` los tecleó Juan
José). **Origen:** observación de #84: con el modo Tor activo, el otro par de WireGuard siguió
mandando UDP/51820, el kernel contestó "puerto inalcanzable" (ICMP 3/3) y el vigilante lo contó
como fuga. La marca de conntrack de #101 no lo cubre: esa conexión la empezó el otro, no tor.

## Entorno

- ISO de `main` `42e95ae` (`0efbfb677906c6c3…`) instalada en QEMU con Secure Boot
  (`install-in-qemu.sh --secure-boot arrancar`), pcap del hipervisor en
  `repro/out/ci-main-42e95ae/v100-icmp.pcap` (sha256 `8785631d16a5f93f…`, fuera del repo).
- Rojo (18-nov): tabla de #101 (sha256 `d975f862c9e09f0f…`).
- Verde (19-nov): misma instalación con `nimbo-nav_0.1.4-1_all.deb` (sha256 `ad74d3e4c3194d70…`)
  instalado con `dpkg -i`; tabla `85c44796b77a1717…`, la de este PR byte a byte. Pcap del
  hipervisor: `repro/out/ci-main-42e95ae/v100-icmp-verde.pcap` (sha256 `b3c22efa15b2c695…`).
- Prueba: `pruebas/prueba-icmp-entrante.sh`, desde el disco de herramientas. Un namespace
  `nimbo-par` unido por un veth hace de otro par y manda 3 UDP a `10.251.0.1:51820`, donde no
  escucha nadie. Primero sin modo Tor (control) y luego con el modo Tor activo. Se miran el
  contador `fugas` y los ICMP 3/3 que recibe el par.

## Resultados

| Pasada | ICMP 3/3 recibidos por el par | Fugas | Líneas `nimbo-fuga` | Veredicto |
|---|---|---|---|---|
| Control, sin modo Tor ([captura](2026-11-18-icmp-entrante/1-rojo-tabla-0x6e74.png)) | **3/3** | — | — | el kernel genera el ICMP: la prueba vale |
| Modo Tor, tabla de #101 (misma captura) | **0** | **0 → 3 (+3)** | `OUT=nimbo-v0 SRC=10.251.0.1 DST=10.251.0.2 … PROTO=ICMP TYPE=3 CODE=3` | **ROJO** |
| Control, sin modo Tor ([captura](2026-11-18-icmp-entrante/2-verde-tabla-0.1.4-1.png)) | **3/3** | — | — | la prueba vale |
| Modo Tor, tabla de 0.1.4-1 (misma captura) | **3/3** | **0 → 0 (+0)** | ninguna | **VERDE** |

En ninguno de los dos pcap del hipervisor aparece un paquete de `10.251.0.0/30`: todo quedó en el veth.
Lo que sale al cable son las conexiones de tor con sus relés, DHCP y NDP/MLD.

**Conclusión (rojo):** el ICMP de error que el kernel manda a tráfico que llega de fuera se
descarta y cuenta como fuga, aunque no sale nada del navegador. Arreglo (checkpoint aceptado por
Juan José el 19-nov, opción A): aceptar `ct direction reply ct state related` solo para
ICMP/ICMPv6, en `nimbo-nav` 0.1.4-1.

**Conclusión (verde):** con 0.1.4-1 el ICMP llega al par y el contador no se mueve.

**Sin regresión de #101** (`pruebas/prueba-rst-kernel.sh`, misma captura, misma tabla): con 2
conexiones de tor con relés, matar tor deja las fugas en 0 → 0 (+0) a los 30 s, y la **prueba
negativa** (conexión directa de `nobody` a `1.1.1.1:443`) sigue contando: **+2**. En el pcap del
hipervisor no hay ningún paquete hacia `1.1.1.1`: se contó y se descartó sin salir al cable.

## Límites

- Se probó con UDP a un puerto cerrado (el caso de #84). Otros ICMP de error del kernel
  (p. ej. "fragmentación necesaria") siguen la misma regla, pero no se midieron.
- Las respuestas con datos y los RST del kernel a conexiones **entrantes** siguen contando como
  fuga: es intencionado (un servicio que escuche no debe contestar fuera de Tor).
