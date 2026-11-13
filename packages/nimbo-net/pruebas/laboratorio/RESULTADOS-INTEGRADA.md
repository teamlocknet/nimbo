# RF-RED-01 sobre la ISO integrada instalada

ISO de main d114b8e3acb9a2297c369d7df42ac2db8cc61dd6, compilada por
[build-iso.yml, run 43346092320](https://github.com/teamlocknet/nimbo/actions/runs/43346092320). SHA-256 completo:

`30b5958fab71595533d67a6ee630bb6a531ed87f085f1c8260f80f39f0eda732`

Tamaño: 572522496 bytes. [repro-verify 43346092325](https://github.com/teamlocknet/nimbo/actions/runs/43346092325): las dos piernas
coinciden con el artifact descargado. Esta imagen no es el candidato de
release 03ff84c ni la ISO local del 9 de noviembre.

Dos discos independientes de 20 GiB, instalados mediante Calamares con LUKS2,
UEFI y Secure Boot, zona America/Bogota. Teclado A: US; B: Spanish/Predeterminado.
Para controlar B se usa setxkbmap us solo en la sesion grafica. Tras instalar, arranque
desde disco sin ISO live y sin kernel/initrd externo. Host WSL, QEMU 10.0.13,
TCG, 2 vCPU y 2048 MiB por VM. LAN privada compartida; DHCP restringido,
sin configurar TAP ni cambiar el firewall del host.

Instrumentación: CD auxiliar de solo lectura con agente-vm.py y
agente-integrado.py, ejecutado manualmente con sudo después del login.
El agente no instala paquetes, no aplica sysctl y no sustituye unidades.
Captura pasiva AF_PACKET; no se instala tcpdump. Contraseñas propias
efímeras del ensayo; no se exportan credenciales ni claves WireGuard privadas.
Los discos instalados son cifrados y desechables; apagarlos no borra su contenido.

## Resultado: 64 comprobaciones correctas

Ambas VMs: raíz ext4, sin medio live montado, LUKS2 y Secure Boot activos;
red física apagada al arrancar. Kernel 6.1.0-52-amd64. Los cinco módulos
están instalados; nimbo-net 0.1.0-1 y nimbo-red 0.1.1-1.

verify-hardening: 0 fallos en 44 comprobaciones por VM. El archivo
/etc/sysctl.d/99-zz-nimbo-hardening.conf tiene SHA-256
1f9bb1492d11b306946da5b988ef6c21c3331299f9b1cda7fb19a007146e5e48,
igual que security/hardening/3b2/sysctl/99-zz-nimbo-hardening.conf. No se
aplicó manualmente sysctl: se midió el hardening del instalado.

- Alias en ambas: add lo ignora; set aplica nimbo-lab:probe. La sonda retira
  su interfaz temporal. El join real registra su alias nimbo-net y su ifindex.
- Preparación separada: cada VM genera su clave localmente y solo exporta la
  pública. Perfiles preparados antes de la aceptación.
- Se ejecuta nimbo-red on antes del join; direcciones físicas 10.0.2.15/.16.
  Túnel dividido 10.90.0.1/.2. Un solo join inicial por equipo: ambos devuelven 0.
- Handshake en ambos. Tres pings por dirección: 3 transmitidos, 3 recibidos,
  0 % de pérdida.
- Con el túnel activo: all=1, default=1, enp0s3=1 y wg-nimbo=1 en ambas.
  El valor efectivo es 1: max(all, interfaz), modo estricto.
- Tras leave: DNS y ruta por defecto conservados, sin rutas de wg-nimbo.
- VPN primero: Tor se niega; VPN conservada y Tor inactivo, en ambos equipos.
- Tor primero: join se niega; Tor conservado y sin wg-nimbo, en ambos equipos.
- Tres rondas simultáneas, objetivos A/B/A: Tor devuelve 0 y join devuelve 1;
  nunca se observan ambos modos activos. El otro par agota la espera y limpia.
- Limpieza final: Tor apagado, túnel retirado, nimbo-red off y sin dhclient.
  Las dos VMs se apagaron; sus pidfiles desaparecieron.

## Capturas de la fase positiva

El patrón emitido por ping es 6e696d626f2d6c61622d313233343536 (15 bytes).
Por VM: interfaz física, 24 paquetes y 3856 bytes de PCAP, 18 paquetes
UDP/51820 y 0 paquetes con el marcador; wg-nimbo, 12 paquetes y 1224 bytes
de PCAP, los 12 con el marcador. Son capturas pasivas, sin instalar tcpdump.
ANALISIS-PCAP.json contiene los recuentos; los cuatro PCAP suman 10160 bytes.

## Contador de Tor durante la concurrencia

En Tor primero, el contador fue 0 y no hubo entradas nimbo-fuga.
En las tres rondas concurrentes se observaron, respectivamente:

| Ronda | VM con Tor | Contador nft | Bytes |
| --- | --- | ---: | ---: |
| 1 | A | 4 | 816 |
| 2 | B | 5 | 1020 |
| 3 | A | 4 | 816 |

El journal registra respuestas ICMP tipo 3, código 3 (puerto inaccesible),
que citan intentos UDP/51820 del otro par. Son respuestas bloqueadas por la
tabla Tor; nimbo-leakcheck marcó limpio=false. En la segunda ronda el JSON
muestreaba 4 descartes mientras nft ya mostraba 5; se conservan las dos muestras.

Este aviso requiere que Emmanuel/Juan José valoren cómo clasifica nimbo-nav
esas respuestas automáticas. La exclusión VPN/Tor se mantuvo. Los PCAP cubren
la fase positiva, no las rondas concurrentes; para estas se guardaron nft y
journal. No se afirma contador de fugas cero durante la concurrencia.

## Evidencia y alcance

[Evidencia completa](evidencia/integrada-d114b8e/) con procedencia, piernas
A/B, resultados JSON, comprobaciones, análisis PCAP, comandos QEMU, resúmenes
y fin de Calamares, fuentes exactas del CD auxiliar y SHA256SUMS.
La copia versionada del agente en laboratorio/ corrige un comentario sobre
RAM; instrumentacion/ conserva los bytes realmente ejecutados. No hay claves
privadas ni credenciales en los archivos publicados.

Firmware OVMF del snapshot 20260901T000000Z, paquete
ovmf_2022.11-6+deb12u2_all.deb: SHA-256
e73d3d1a8799f7f6fc16b73501d913edcdd86237556fbff30693e747e6dc262e.
OVMF_CODE_4M.secboot.fd: d50189a486d22af418198226a3a5bcb6ddac775590f6a808bd629474ee034d62.
Plantilla OVMF_VARS_4M.ms.fd: e6044c5d1fd81998a5967d907ec425e48da534832c7d9b0b4c7a702b62019c50.
Cada VM tuvo su propia copia de NVRAM.

[Procedimiento](README.md#aceptación-sobre-sistemas-instalados). Los comandos
QEMU registrados usan rutas locales que deben adaptarse al reproducir. La
prueba se realizó el 12-nov-2026, America/Bogota. Esta serie finita demuestra
los casos observados; no cubre todas las carreras posibles, CGNAT, bootstrap
de Tor ni navegación. La aceptación del pendiente de ADR-011 la revisa Juan José.
