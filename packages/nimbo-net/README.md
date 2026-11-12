# nimbo-net

Implementacion inicial de RF-RED-01 / HU-09: WireGuard directo entre dos pares
preparados. Interfaz `wg-nimbo`, compatible con la barrera del modo Tor (#59).
Sin daemon, servicio de arranque, DHCP, DNS, NAT, forwarding ni ruta por defecto.
No se instala una tabla nftables: no hay necesidad de reglas propias en este
alcance. Solo se consulta si existe `inet nimbo_tor`; nunca se vacia el ruleset.

Estado: 32 pruebas simuladas aprobadas en bookworm; .deb construido e instalado
en contenedor con nimbo-red. Ayuda, status y rechazo de join sin perfil correctos.
Pendientes lintian, dos VMs, rp_filter=1, coexistencia/concurrencia con Tor,
captura, hermetismo y posterior integracion ISO con checkpoint. No entregar
como VPN validada antes de completar esas mediciones. ADR-011: PR #65.
Detalle de evidencia y limites: VALIDACION.md.

## Preparacion previa (no cuenta como join)

Cada equipo genera su clave localmente. Instalar las herramientas desde los
paquetes aprobados; no se descarga nada al ejecutar join. Crear /etc/nimbo-net
como root:root 0700, private.key y perfil.json root:root 0600. No usar symlinks
ni hardlinks. Nunca copiar claves privadas al otro equipo ni al repositorio.

Ejemplo de generacion local (no muestra la clave privada y no sobrescribe):

```bash
sudo install -d -m 0700 /etc/nimbo-net
sudo sh -c 'set -euC; umask 077; wg genkey > /etc/nimbo-net/private.key; wg pubkey < /etc/nimbo-net/private.key > /etc/nimbo-net/public.key'
```

Intercambiar solo la clave publica y los datos del par, confirmando su origen.
Preparar perfil.json en cada equipo; sustituir el marcador de clave publica:

```json
{
  "version": 1,
  "address": "10.90.0.1",
  "peer_address": "10.90.0.2",
  "peer_public_key": "SUSTITUIR_POR_CLAVE_PUBLICA_DEL_OTRO_EQUIPO",
  "endpoint": "192.0.2.2",
  "endpoint_port": 51820,
  "listen_port": 51820,
  "timeout": 120
}
```

192.0.2.2 es una direccion documental: sustituirla por la IP numerica alcanzable
del otro equipo. En el segundo perfil se invierten direcciones del tunel y se
usan clave publica y endpoint del primero. Elegir direcciones privadas que no
coincidan con redes/rutas ya existentes. El ejemplo no contiene claves reales.
No se admiten campos extra, hooks, IPv6 o prefijos de ruta arbitrarios.

## Activacion

```bash
sudo nimbo-red on
sudo nimbo-net join
nimbo-net status
sudo nimbo-net leave
sudo nimbo-red off
```

La preparacion y nimbo-red on son previos: la aceptacion de RF-RED-01 cuenta
un join por equipo, con perfiles y conectividad listos. Ejecutar join en ambos
equipos dentro de la ventana de espera (120 intentos con este perfil). Se espera
handshake y ping al par: si su firewall bloquea ICMP, no se declara conectado.
Las operaciones tienen tiempos acotados por herramienta, ademas del numero de
intentos; timeout no es una garantia estricta de duracion total en segundos.

status es pasivo y no usa credenciales: presencia de interfaz no significa que
el peer sea alcanzable ni que pertenezca a nimbo-net. Join repetido comprueba
el tunel propio sin duplicarlo; si falla sobre un tunel ya existente, lo conserva
para inspeccion/leave. Un fallo en una nueva activacion intenta limpiar lo propio.
Si la limpieza falla, no se anuncia silencio: usar status/leave y revisar.

Estado temporal protegido en /run/nimbo-net; la identidad de la interfaz usa
ifindex y alias aleatorio para no borrar interfaces ajenas. El bloqueo serializa
operaciones de nimbo-net, no las operaciones del modulo Tor. Un apagado abrupto
puede requerir leave; tras reiniciar no se restaura la interfaz automaticamente.
Leave elimina el tunel y sus rutas asociadas; conserva la NIC y la concesion DHCP.

Tor y VPN se excluyen: join comprueba unidad y tabla antes de crear el tunel,
despues de crearlo y durante la espera. nimbo-tor rechaza wg-nimbo. Esto no prueba
exclusion atomica entre procesos; activacion concurrente pendiente en dos VMs y
revision con Emmanuel antes de cerrar la aceptacion.

## Pruebas

Pruebas locales sin modificar la red (biblioteca estandar):

```bash
cd packages/nimbo-net
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Contrato bookworm (desde la raiz del repo):

```bash
sudo env CONTAINER_ENGINE=docker ./ci/test-modulo-en-bookworm.sh packages/nimbo-net
```

El runner usa pytest, que recoge tambien unittest. Estos tests simulan wg, ip,
nft y systemctl: no requieren herramientas de red extra para ejecutarse.
No ejecutar join real en el anfitrion para validar los tests.

## Limites

Sin CGNAT garantizado, relay, Wi-Fi ni tunel completo. Mantener rp_filter=1 y
medirlo en ambas VMs, incluida su interfaz fisica y wg-nimbo. No se cambia sysctl.
No hay soporte de activacion simultanea con Tor ni de administradores de red
externos modificando el mismo tunel. El paquete fuente quilt y reproducibilidad
del .deb quedan pendientes; no se heredan las pruebas de nimbo-audit.
