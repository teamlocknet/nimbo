# Validacion de nimbo-net ? 11-nov-2026

Estado: implementacion local inicial; no publicada, no integrada en la ISO.
Rama alejandro/nimbo-net, base main 8d01002. ADR-011 en PR #65 (pendiente de review).
Alcance aprobado por Juan Jose: WireGuard directo, dos pares preparados,
wg-nimbo, red fisica a cargo de nimbo-red, Tor excluyente, rp_filter=1.

## Ejecutado en esta sesion

- Rojo inicial: unittest no puede importar nimbo_net, aun inexistente.
- Implementacion inicial: 22 pruebas aprobadas con ejecutor de sistema simulado.
- Diez casos adicionales: rojo en endpoint JSON entero y directorio de estado
  de nimbo-red escribible por otros; ambos corregidos antes del verde final.
- Verde final: 32 pruebas, 0 fallos, Python 3.13 del anfitrion WSL.
- git diff --check correcto. Metadatos pyproject y control preparados.
- No se modificaron interfaces, rutas, nftables, sysctl o servicios del host.
- Los tests usan identidades sinteticas generadas en memoria/temporales por
  prueba; no hay claves privadas de ejemplo guardadas en el repositorio.

Los registros inicial y final estan en /tmp/nimbo-net-rojo.log y
/tmp/nimbo-net-verde.log (temporales del host, no artifacts permanentes).

## Contrato simulado cubierto

Activacion con /32 del peer, espera de handshake y ping, ausencia de DHCP y
rutas por defecto; rechazo de Tor activo, transiciones, tabla residual y errores
de consulta; Tor que comienza despues de crear interfaz; bloqueo de operaciones
simultaneas del modulo; limpieza tras fallo de wg o timeout; interfaz ajena,
ifalias/ifindex distintos y estado corrupto; limpieza fallida conserva estado;
status sin privilegios y sin activacion; permisos debiles, symlink, hardlink,
JSON duplicado, campos extra, datos invalidos y secretos ausentes de salida.

## Bookworm pendiente

Desde la raiz del repo, sin ejecutar join en el host:

```bash
sudo env CONTAINER_ENGINE=docker ./ci/test-modulo-en-bookworm.sh packages/nimbo-net
```

El runner existente instala python3 y python3-pytest, y pytest descubre las
pruebas unittest. No necesita instalar wg/ip/nft para estos tests simulados.
No afirmar equivalencia con bookworm hasta observar la ejecucion.
El .deb tambien requiere build e instalacion separados, con nimbo-red disponible;
no se heredan resultados de nimbo-audit. Fuente quilt y reproducibilidad pendientes.

## Aceptacion real pendiente, dos VMs/equipos

1. Preparar herramientas y perfiles protegidos, cada equipo genera su clave local.
   Configurar red de laboratorio con endpoints alcanzables, sin CGNAT prometido.
2. Aplicar hardening vigente y registrar rp_filter efectivo en all, default,
   interfaz fisica y wg-nimbo cuando exista. Mantener 1: no cambiar sysctl.
3. Antes de join, comprobar ausencia de wg-nimbo y sockets VPN; medir 0/0 global
   en el arranque de la ISO integrada, no inferirlo de estos tests.
4. Activar NIC con nimbo-red on, y ejecutar un join en cada VM dentro de la ventana
   de espera. Comprobar handshake y trafico bidireccional. Registrar rutas y DNS
   antes/despues para comprobar que nimbo-net no los cambia fuera del peer.
5. Capturar en NIC y tunel por separado: marcador de prueba solo en el tunel,
   transporte WireGuard en la NIC. No versionar claves ni capturas con secretos.
6. Tor primero: join se niega. VPN primero: nimbo-tor on se niega por wg-nimbo.
   Probar tambien intentos concurrentes con Emmanuel; las comprobaciones actuales
   no garantizan exclusion atomica. Si hay carrera, resolver mediante checkpoint.
7. Leave retira solo recursos propios, preserva NIC y recursos Tor/ajenos.
   Tras nimbo-red off medir silencio global. Reinicio no restaura la VPN.
8. Probar peer inaccesible, fallo de configuracion y errores de limpieza. Si la
   identidad del enlace cambio, se conserva por seguridad y se informa fallo.
9. Integracion ISO y job CI en un checkpoint separado; MATCH, QEMU, RAM y
   hermetismo del commit integrado con Juan Jose antes de cerrar RF-RED-01.

Ninguna prueba de handshake real, cifrado por captura, rp_filter, Tor real,
QEMU, hermetismo o instalacion de paquete ha sido ejecutada en esta sesion.

## Bookworm ejecutado por Alejandro

Comando: sudo env CONTAINER_ENGINE=docker
./ci/test-modulo-en-bookworm.sh packages/nimbo-net.
Imagen: docker.io/library/debian@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171.
Snapshot: 20260901T000000Z. Python 3.11.2-1+b1, pytest 7.2.1-2.
Resultado observado: 32 passed in 0.15s. No paquetes APT adicionales.
Sigue siendo red simulada: no acredita handshake real ni rp_filter medido.
Build, instalacion y lint del .deb siguen pendientes.

## Build binario bookworm observado en la salida de Alejandro

Comando: sudo env CONTAINER_ENGINE=docker ./packages/nimbo-net/build-deb.sh.
Salida /tmp/nimbo-net-deb.6gl7Qd; nimbo-net_0.1.0-1_all.deb.
Pybuild: 32 passed in 0.17s. SHA-256 mostrado por el constructor:
0c262fcbce04371ef73af0336c5f87a9be2510a3b5a1809e2280114470048e20.
Dependencias mostradas: python3:any, wireguard-tools, iproute2, iputils-ping,
nftables, systemd y nimbo-red. No se pudo releer el artifact como usuario sin
privilegios porque su directorio temporal, creado con sudo, es root 0700.
Pendientes instalacion, lintian y VPN real. El paquete no incluye pagina man.
Fuente quilt y reproducibilidad siguen sin validar.

## Instalacion observada en bookworm

Alejandro ejecuto test-deb.sh /tmp/nimbo-net-deb.6gl7Qd. El contenedor construyo
nimbo-red con 16 tests aprobados e instalo nimbo-red y nimbo-net 0.1.0-1 junto
con dependencias APT reales. /usr/bin/nimbo-net --help funciona; status muestra
inactivo; join sin perfil devuelve 1. La comparacion ip -j link antes/despues
no encuentra cambios y wg-nimbo no existe. Resultado final OK.
El hash del paquete servido sigue siendo
0c262fcbce04371ef73af0336c5f87a9be2510a3b5a1809e2280114470048e20.

Versiones observadas: iproute2 6.1.0-3; iputils-ping 3:20221126-1+deb12u1;
nftables 1.0.6-2+deb12u2; systemd 252.39-1~deb12u2;
wireguard-tools 1.0.20210914-1+b1. Log esperado en el directorio de artifacts:
test.log. Este resultado acredita instalacion y operaciones pasivas, no un
handshake, cifrado, rp_filter ni hermetismo global.

Pendientes actuales: lintian; dos VMs y exclusividad con Tor, incluida
concurrencia; rp_filter=1 medido; integracion ISO/CI con checkpoint; MATCH y QEMU.
