# Resultado del laboratorio de red privada

La repetición sobre la ISO integrada instalada está en
[RESULTADOS-INTEGRADA.md](RESULTADOS-INTEGRADA.md). Este documento conserva
el ensayo live anterior y su alcance.

Base del código: main `6821936`. Debian bookworm, kernel `6.1.0-52-amd64`,
dos VMs QEMU/TCG con 1536 MiB cada una. ISO live instrumentada temporalmente;
no es una validación de la integración final ni de Secure Boot.

## Resultados observados

- Ambas VMs: handshake WireGuard y tres pings al par, 0 % de pérdida.
- Alias ignorado en `ip link add`, aplicado en `ip link set`: confirma la corrección.
- `rp_filter`: all=1, default=1, wg-nimbo=1; ens3=0. El kernel aplica el mayor
  valor entre all y la interfaz: el valor efectivo en ens3 era 1 (modo estricto),
  al igual que en wg-nimbo. Se midió con el hardening vigente de 3B.2 aplicado
  explícitamente mediante sysctl -p; véase el detalle siguiente.
- El patrón realmente emitido por ping aparece en la captura del túnel y no en
  la captura de ens3, en ambas VMs. `resultado-capturas.json` usa ese patrón
  de 15 bytes; la primera comprobación había buscado incorrectamente 16 bytes.
- WireGuard conectado primero: `nimbo-tor on` devuelve 2; Tor queda inactivo.
- Tor activo primero, con tabla inet nimbo_tor: join devuelve 1 sin crear wg-nimbo.
- Tres rondas simultáneas de join y Tor en A: Tor devuelve 0 y join devuelve 1.
  Estado final en A: Tor activo sin wg-nimbo. B agota su espera y limpia su interfaz.
- leave y nimbo-red off completan correctamente. Ambas VMs quedan apagadas.

## Alcance y pendientes

Se usaron el código, unidades y reglas reales de nimbo-nav; sus archivos se
copiaron como instrumentación, sin construir su paquete Debian. Tor 0.4.9.11
se instaló desde el snapshot verificado. El laboratorio bloquea la salida a Internet:
no demuestra bootstrap de Tor, navegación ni ausencia de fugas de su navegador.
Las tres rondas comprueban los resultados observados; no muestrean toda transición
ni demuestran ausencia de todas las carreras posibles.

La preparación de perfiles fue previa; cada VM generó su clave privada localmente.
El intento inicial sin perfil no forma parte de la aceptación; con perfiles preparados
se ejecutó un join por equipo y ambos conectaron. No se guardaron claves privadas.

Juan José debe revisar estas evidencias antes de pasar ADR-011 a Aceptado.
Siguen pendientes la integración oficial en ISO, MATCH ×2 y hermetismo de esa imagen.
Los archivos de evidencia tienen hashes en evidencia/SHA256SUMS.

## Procedencia exacta de la ISO y preparación

ISO local: `live-image-amd64.hybrid.iso`, 481296384 bytes, SHA-256:

```
243769073218934f7813cb8c10978a401937fdcbe5101e3b5305c6509f8cbe9f
```

Es la compilación local mostrada el 9-nov por Alejandro, usando Docker y el
espejo local del snapshot 20260901T000000Z. No es la ISO de CI del commit
03ff84cd1804908cbd1fd7cdb90c0e8c1734a5fa (28760694…).
El log conservado inicia el 9-nov a las 01:22:46 UTC y termina a las 01:29.
El SOURCE_DATE_EPOCH 1794186923 coincide con el commit
42031e1c355e7236c8b1dd129637792046f1107a. Esto identifica el anclaje temporal,
pero no acredita un checkout limpio: el log no guarda el estado completo del
árbol de trabajo de aquella compilación. No atribuimos la ISO a una receta
exacta de ese commit sin esa evidencia. El campo base_commit del manifiesto
original identifica el código de módulos ensayado (6821936), no su compilación.

Se arrancó la ISO de solo lectura, extrayendo /live/vmlinuz y /live/initrd.img.
Al initrd se concatenó un archivo cpio con un hook live-bottom y su ORDER:
crea una unidad temporal que monta el segundo CD, NIMBO_NET_LAB, y ejecuta
agente-vm.py por ttyS1. No se reempaquetó ni escribió la ISO original.
QEMU usó TCG, dos vCPU, 1536 MiB por VM, consola ttyS0 y control por socket
Unix en ttyS1. Las NIC virtio compartieron un hub/socket local con DHCP de
QEMU y restrict=on, sin TAP ni salida a Internet. Los comandos de arranque,
el hook y ORDER se conservan en evidencia/instrumentacion/; las rutas se
refieren al directorio temporal del ensayo y deben adaptarse al repetirlo.

El segundo CD aportó nimbo-net 0.1.0-1 (SHA-256
34421c814b8c0dd6e327fe3ca08ffee246087d9e5aaa1ce0deed459ee8be5533),
wireguard-tools 1.0.20210914-1+b1, tcpdump 4.99.3-1 y libpcap0.8 1.10.3-1.
Para Tor se añadieron tor 0.4.9.11-0+deb12u1, libevent-2.1-7
2.1.12-stable-8, runit-helper 2.15.2 y lsb-base 11.6. Los paquetes Debian
se cotejaron con Packages, cuyo hash se cotejó con el InRelease firmado.
El paquete auxiliar nimbo-red se ensambló para el ensayo desde su código
Python en 6821936; no se presenta como una nueva validación de su receta Debian.
El código, unidades y tabla de nimbo-nav también proceden de 6821936.

Para repetir con identidad de bytes hace falta conservar esta ISO local:
los archivos publicados no permiten reconstruir por sí solos su árbol de
compilación original. Una repetición sobre la ISO oficial debe registrar su
SHA/run propios y no heredar la procedencia de este ensayo.

## Archivo sysctl aplicado y contador de fugas

Se copió exactamente security/hardening/3b2/sysctl/99-zz-nimbo-hardening.conf
del commit 682193648ecea7ef9d4a768f2a8f3e3215255d79 a /run/nimbo-lab/hardening.conf
y se aplicó con `sysctl -p /run/nimbo-lab/hardening.conf`. Retornó 0 en ambas VMs,
sin stderr. SHA-256 del archivo aplicado:

```
1f9bb1492d11b306946da5b988ef6c21c3331299f9b1cda7fb19a007146e5e48
```

Las respuestas de preparación y una copia del archivo se incluyen como evidencia.
La regla del máximo está documentada en el kernel:
https://docs.kernel.org/networking/ip-sysctl.html#rp-filter

No se recogió el contador fugas de nimbo-nav ni su estado de leakcheck durante
las rondas simultáneas. Se guardaron las tablas presentes, no sus contadores.
Por tanto, no podemos afirmar si hubo un paquete WireGuard contado como fuga
ni descartar un falso positivo; queda como medición opcional pendiente.
