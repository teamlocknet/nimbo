# Validación de nimbo-net — 11-nov-2026

Estado: corrección local del PR #66 tras la revisión de Juan José.
La implementación no está integrada en la ISO ni validada entre dos VMs.
Base: main 8d01002; contrato ADR-011 en PR #65.

## Resultado actual y bloqueo corregido

Juan José reprodujo con iproute2 6.1.0 y kernel 7.2 que ip link add no
aplica el alias. El simulador anterior aplicaba el alias y ocultaba el fallo:
join dejaba wg-nimbo creada sin estado, bloqueando nuevos join, leave y Tor.

Rojo: simulador corregido para ignorar alias en add. Resultado observado:
35 tests, 13 fallos y 1 error. Registro local /tmp/nimbo-net-alias-rojo.log.

Arreglo: add sin alias; set alias inmediatamente después; leer ifindex y
registrar estado. Si set o lectura inicial fallan, borrar por nombre la interfaz
recién creada. Add con EEXIST no autoriza limpiar una interfaz ajena.
Después de identificarla, la limpieza exige ifindex y alias; si falla,
no se anuncia silencio y se conserva el estado cuando existe.

Verde local: **35 tests aprobados**, Python 3.13 del anfitrión WSL, red
simulada. Casos nuevos: fallo de set alias, fallo de lectura inicial y carrera
con EEXIST. Registro /tmp/nimbo-net-alias-verde.log.
Falta repetir bookworm y comprobarlo en kernel 6.1 de la VM. Estos registros
son temporales del host; no sustituyen evidencia de un kernel real.

## Resultados anteriores al arreglo

| Prueba | Resultado observado |
|---|---|
| Rojo inicial | Módulo nimbo_net ausente |
| Primer verde local | 22 tests; luego 32 tras corregir dos validaciones |
| Bookworm, script genérico | 32 passed in 0.15s, Python 3.11.2-1+b1 y pytest 7.2.1-2 |
| Primer build | 32 passed in 0.17s; paquete 0.1.0-1 all |
| Instalación en contenedor | nimbo-red construido con 16 tests; ambos paquetes instalados; ayuda y status correctos; join sin perfil devuelve 1 sin crear interfaz |
| Lintian 2.116.3+deb12u1 | Sin etiquetas E; initial-upload-closes-no-bugs y no-manual-page |
| Build con manual | 32 passed in 0.16s; manual gzip de 1199 bytes incluido |

Imagen anclada:
`docker.io/library/debian@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171`.
Snapshot: `20260901T000000Z`.

Primer artifact: `/tmp/nimbo-net-deb.6gl7Qd`, SHA-256
`0c262fcbce04371ef73af0336c5f87a9be2510a3b5a1809e2280114470048e20`.
Build con manual: `/tmp/nimbo-net-deb.lqK2AZ`, SHA-256
`7042584603fc2011550865a04828e630b09ce23b24396ff187f90994ef56d0e8`.
**Ambos contienen el fallo de alias. Ninguno acredita la corrección actual.**
Los resultados proceden de las salidas ejecutadas por Alejandro; el primer
artifact no pudo releerse como usuario sin privilegios por su directorio root 0700.

Dependencias observadas: iproute2 6.1.0-3; iputils-ping 3:20221126-1+deb12u1;
nftables 1.0.6-2+deb12u2; systemd 252.39-1~deb12u2;
wireguard-tools 1.0.20210914-1+b1; nimbo-red 0.1.0-1.

El manual y su comprobación se agregan para resolver no-manual-page.
No existe bug de Debian asociado: no se inventa un Closes para silenciar el
aviso del empaquetado inicial. Instalación y lintian del manual pendientes.

## Comandos para validar el arreglo

Desde la raíz del repositorio, sin activar la VPN en WSL:

```bash
sudo env CONTAINER_ENGINE=docker ./ci/test-modulo-en-bookworm.sh packages/nimbo-net
sudo env CONTAINER_ENGINE=docker ./packages/nimbo-net/build-deb.sh
# Usar el directorio NUEVO mostrado por el build:
sudo env CONTAINER_ENGINE=docker ./packages/nimbo-net/test-deb.sh <directorio-nuevo>
sudo env CONTAINER_ENGINE=docker ./packages/nimbo-net/lint-deb.sh <directorio-nuevo>
```

## Aceptación real pendiente

- Dos VMs/equipos: cada equipo genera su clave localmente y prepara su perfil;
  un join por equipo, handshake y tráfico bidireccional.
- Kernel 6.1: confirmar la creación, asignación del alias y limpieza real.
- Hardening aplicado: medir rp_filter=1 efectivo en all, default, interfaz
  física y wg-nimbo con el túnel arriba. No cambiar sysctl.
- Capturas en NIC y túnel, rutas y DNS antes/después; no publicar claves.
- Tor primero, VPN primero e intentos concurrentes con Emmanuel. El bloqueo
  local de nimbo-net no acredita exclusión atómica con Tor.
- Leave y fallos retiran solo lo propio; tras nimbo-red off medir silencio
  global. Reinicio no restaura la VPN.
- pruebas/recoger-evidencia.py y su guía están preparados; solo sintaxis y
  ayuda comprobadas, no ejecutados en VMs reales.

## Checkpoints separados

wireguard-tools **no está en la ISO actual**. Su incorporación requiere
checkpoint de Juan José: hermetismo, comprobar que wg-quick@ no queda
habilitado, MATCH x2 y QEMU. No se modifica CI, ISO, Tor ni hardening aquí.
Juan José agregará nimbo-net a tests-modulos-bookworm en ci.yml en otro PR.
Fuente quilt y reproducibilidad del .deb siguen sin validar.

## Bookworm después de corregir el alias

Alejandro ejecutó ci/test-modulo-en-bookworm.sh packages/nimbo-net con Docker,
imagen por digest y snapshot indicados arriba. Python 3.11.2-1+b1 y
python3-pytest 7.2.1-2. Resultado: **35 passed in 0.14s**, sin APT adicional.
Incluye simulación de alias ignorado en add, limpieza ante fallo de set/lectura
y protección de EEXIST. No es una prueba del kernel real: sigue pendiente
la confirmación en kernel 6.1 y las dos VMs. Falta reconstruir el paquete
corregido, instalarlo y repetir lintian.

## Paquete con el arreglo del alias construido

Alejandro ejecutó build-deb.sh; pybuild aprobó 35 tests en 0.17s.
Artifact: `/tmp/nimbo-net-deb.urG0zL/nimbo-net_0.1.0-1_all.deb`.
SHA-256: `34421c814b8c0dd6e327fe3ca08ffee246087d9e5aaa1ce0deed459ee8be5533`.
Hash y metadatos releídos desde WSL. Manual gzip incluido (1199 bytes).
Pendientes instalación y lintian de ESTE paquete, y kernel/VMs reales.

## Instalación del paquete corregido

Alejandro ejecutó test-deb.sh sobre /tmp/nimbo-net-deb.urG0zL.
Resultado: nimbo-net y nimbo-red 0.1.0-1 instalados; ayuda correcta; manual
presente e íntegro (gzip); status inactivo; join sin perfil devuelve fallo
sin crear interfaz ni cambiar los enlaces. El constructor de nimbo-red
aprobó 16 tests en 0.08s. SHA-256 mostrado por el contenedor:
34421c814b8c0dd6e327fe3ca08ffee246087d9e5aaa1ce0deed459ee8be5533.
No se activó una VPN real: kernel 6.1 y dos VMs siguen pendientes.

## Lintian del paquete corregido

Alejandro ejecutó lint-deb.sh /tmp/nimbo-net-deb.urG0zL.
Lintian 2.116.3+deb12u1: sin etiquetas E y sin no-manual-page.
Único aviso de paquete: initial-upload-closes-no-bugs, justificado porque
no existe bug Debian asociado. El proceso avisa de privilegios root dentro
del contenedor. Con esto quedan comprobados build (35 tests), instalación,
manual y lintian del artifact 34421c814b8c0dd6e327fe3ca08ffee246087d9e5aaa1ce0deed459ee8be5533.
No cambia el pendiente de kernel 6.1, dos VMs, Tor, captura y rp_filter=1.
