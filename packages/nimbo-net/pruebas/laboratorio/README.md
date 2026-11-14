# Laboratorio temporal de nimbo-net

Instrumentación para VMs desechables, live o instaladas, sin modificar la ISO original.
El agente corre como root solo dentro de cada VM y recibe acciones limitadas por
un segundo puerto serie conectado a un socket Unix local. No usar en producción.

- `agente-vm.py`: prepara paquetes offline, genera la clave privada dentro de cada
  VM, instala perfiles públicos y ejecuta las comprobaciones.
- `control-vm.py`: envía una acción JSON y recibe su resultado.
- El directorio del laboratorio debe tener modo 0700. Las claves privadas no salen
  de la VM ni aparecen en las evidencias. Solo en la modalidad live, apagar la VM
  destruye sus cambios en RAM; una instalación conserva sus datos en disco.
- `tor_prepare` copia el código y las unidades reales de nimbo-nav para probar la
  exclusión. No construye ni valida el paquete Debian de nimbo-nav.
- `race` ejecuta `nimbo-net join` y `nimbo-tor on` simultáneamente. Una serie finita
  de intentos no demuestra la ausencia de todas las carreras posibles.

El ensayo live original usaba un initrd y paquetes auxiliares fuera del repositorio.
Sus resultados no acreditan una instalación persistente. Las modalidades
integradas siguientes usan los módulos ya incluidos en la ISO; el ensayo instalado
es el que corresponde al pendiente de RF-RED-01. El hermetismo global y las
comprobaciones generales de la ISO siguen teniendo su evidencia independiente.

## Repetición sobre ISO integrada de CI

arrancar-integrada.py exige una ISO cuyo hash coincida con procedencia.json.
Extrae kernel e initrd, concatena solo el hook temporal de control y arranca dos
VMs QEMU/TCG (1536 MiB cada una). La ISO permanece de solo lectura. El segundo
CD contiene los dos agentes Python, con hashes registrados; no contiene claves
ni paquetes. No se reinstalan módulos ni se aplica sysctl desde el agente.

agente-integrado.py reutiliza las acciones del agente anterior, pero rechaza
prepare y tor_prepare. Genera las claves propias en RAM y ejecuta los comandos
instalados en la ISO. Mide el hardening real y el contador fugas. Las capturas
usan AF_PACKET pasivo de Python: Ethernet (DLT 1) en la NIC física y paquetes
IP (DLT_RAW 101) en wg-nimbo, sin instalar tcpdump.

ejecutar-integrada.py registra resultados y comprobaciones, prueba ambos órdenes
de Tor/VPN y tres activaciones concurrentes, y termina apagando las dos VMs.
El caso enabled-runtime de tor@default solo se admite inactivo y con tor.service
disabled, conforme a la evidencia QEMU de #83. Los ensayos usan la sesión live
headless; no acreditan una instalación persistente, Secure Boot ni medición de
RAM del escritorio. La instrumentación temporal no es un servicio del producto.

Ejemplo (rutas persistentes fuera del repositorio):

```sh
python3 packages/nimbo-net/pruebas/laboratorio/arrancar-integrada.py \
  --iso /ruta/ci/live-image-amd64.hybrid.iso --lab /ruta/nuevo-laboratorio \
  --procedencia /ruta/procedencia.json
python3 packages/nimbo-net/pruebas/laboratorio/ejecutar-integrada.py /ruta/nuevo-laboratorio
```

No se incluyen claves privadas en evidencias ni en archivos de control del host.
El SHA de un artifact de PR no se presenta como el SHA del build posterior de main.

## Aceptación sobre sistemas instalados

El ensayo live anterior es diagnóstico. Para cerrar RF-RED-01 se instalan dos
VMs independientes desde la ISO original comprobada, mediante Calamares.
Se arranca cada disco sin la ISO live ni un kernel/initrd externo. Cada equipo
genera su clave WireGuard localmente; no se exportan claves privadas.

El CD auxiliar se prepara en el host desde este directorio:

```sh
xorriso -as mkisofs -V NIMBO_NET_LAB -o /ruta/lab/herramientas.iso \
  agente-vm.py agente-integrado.py
```

El CD auxiliar, montado de solo lectura, contiene agente-vm.py y
agente-integrado.py. Tras iniciar sesión se ejecuta manualmente como root:

```sh
sudo sh -c 'mkdir -p /run/nimbo-lab; mount -o ro /dev/disk/by-label/NIMBO_NET_LAB /run/nimbo-lab; exec python3 -u /run/nimbo-lab/agente-integrado.py'
```

El host conecta el segundo puerto serie a A.serial.sock y B.serial.sock en un
directorio privado (0700). Las VMs comparten una LAN aislada con DHCP; no se
modifica la red del host. Antes de generar perfiles o levantar la red, el arnés
exige raíz ext4, ausencia del medio live y ausencia de IPv4 global en la NIC.

```sh
python3 packages/nimbo-net/pruebas/laboratorio/ejecutar-integrada.py /ruta/lab --instalado
python3 packages/nimbo-net/pruebas/laboratorio/analizar-capturas.py /ruta/lab
```

La primera unión positiva cuenta un solo join por equipo; las denegaciones y
las rondas concurrentes son pruebas posteriores independientes. Se conservan
resultados, capturas y procedencia; nunca los discos, NVRAM ni credenciales.
Las claves de este ensayo instalado residen en los discos cifrados desechables,
no en RAM como en el ensayo live. Apagar una VM instalada no borra su disco.
