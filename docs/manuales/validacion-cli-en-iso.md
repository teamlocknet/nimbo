# PR-B: validacion de nimbo-audit en la ISO

Estado: implementacion local, sin publicar. Base actualizada: main b470a06 (incluye PR #36 a #39).
Fecha: 2026-11-04.

## Comprobaciones ejecutadas

- Sintaxis Bash de constructor, verificadores de ISO, rootfs y sistema instalado.
- Sintaxis POSIX sh de hooks 0180 y 0200.
- git diff --check sin errores.
- Diferencias de workflows limitadas a agregar packages/nimbo-audit/** en
  las listas paths de push y pull_request de build-iso y repro-verify.
- auto/build y auditoria 0210 sin modificaciones.
- Constructor con motor simulado: fuente del CLI montada de solo lectura,
  directorio de receta montado en /build, variables de snapshot y epoch,
  sintaxis del comando interno, compilacion antes de preparar el paquete local
  y antes de lb build. No se ejecutaron Docker ni APT en esta comprobacion.
- Verificador de ISO con motor simulado: resolucion de imagen por digest y
  sintaxis del comando interno. No se extrajo una ISO real.

## Escenarios del verificador rootfs

Se generaron bases de estado dpkg y paquetes .deb temporales con herramientas
Debian reales. gzip tambien se ejecuto realmente. id y chroot se sustituyeron
por comandos simulados: no se ejecuto el CLI dentro de un rootfs real.

| Escenario | Salida observada |
|---|---|
| Fixture limpia | 0 |
| nimbo-audit ausente | 1 |
| Directorio de repositorio temporal presente | 1 |
| Fuente APT temporal presente | 1 |
| Indice APT temporal presente | 1 |
| nimbo-audit dentro del pool persistente | 1 |
| Version de backports dentro del pool | 1 |
| Manual gzip corrupto | 1 |
| CLI sin marca manual | 1 |
| Fallo de ayuda del CLI | 1 |

Estas pruebas validan las guardas del inspector, no la integracion del producto.
Las fixtures se eliminaron al terminar las pruebas.

## Bloqueo observado en el build base

Dos intentos anteriores a integrar el CLI fallaron durante debootstrap por HTTP
503 de snapshot.debian.org. No produjeron ISO. El segundo intento uso epoch
1793814833 y fallo descargando libncursesw6, libproc2-0, logsave, passwd y
readline-common. No son evidencia roja de ausencia del CLI.

El auto/build actual oculta errores al canalizar etapas a tee; su correccion y
los posibles reintentos de descarga estan pendientes de checkpoint separado.

## Pruebas pendientes antes de entregar

1. Build completo del cambio con imagen y snapshot anclados; tests del paquete
   ejecutados dentro de dpkg-buildpackage.
2. Log del hook 0180 con CLI, verify y manual disponibles.
3. Log del hook 0200 con cero nimbo-audit y cero backports en el pool; auditoria
   0210 exitosa.
4. Ejecutar sobre la ISO realmente generada:

```bash
sudo env CONTAINER_ENGINE=docker ./iso/live-build/verificar-cli-en-iso.sh
```

5. Comprobar en el squashfs que no quedan repositorio temporal, fuentes ni
   indices de APT, y que el CLI funciona realmente.
6. Revisiones QEMU live e instalado, hermetismo y RAM con el equipo revisor.
7. Compuerta MATCH entre ejecutores para el commit final.

No se afirma reproducibilidad ni exito del build a partir de las pruebas simuladas.

## Actualizacion del 8 de noviembre

Trabajo trasladado a main b470a06 conservando el respaldo local en git stash.
Conflictos en ambos workflows resueltos conservando la version nueva del espejo
con el unico agregado de packages/nimbo-audit/** a los filtros autorizados.
La correccion de errores de auto/build y la barrera de ISO ausente ya vienen de
main; no se aplica la propuesta alternativa del 4 de noviembre. Se conservan
H-004, ADR-016 y requiredRam 0.75. El inspector de ISO admite NIMBO_ESPEJO.

## Primera ISO del PR-B verificada (8/9 de noviembre)

Base b470a06 mas cambios locales del PR-B. ISO: 476053504 bytes.
SHA-256: bba02034bd645f25d430435f66e946fdea41a55e65fe1817c286362794be3e4b.
El usuario ejecuto el constructor y el inspector sobre el squashfs real con el espejo.
Resultado: nimbo-audit 0.1.0-1, ayuda del CLI y verify utilizables; repositorio
temporal sin rastros; pool de 30 paquetes sin nimbo-audit ni backports; unico
backport del live: calamares 3.3.8-1~bpo12+1. El log de build confirma los hooks
0180 y 0200 y la auditoria 0210 exitosa. Hash comprobado tambien desde el host.
No cubre los cambios posteriores de main #40/#41 ni demuestra MATCH o QEMU.

## Actualizacion posterior a #40/#41

Base actual: main 42031e1. Se conservan idioma, zona y swap de ADR-017 y la
limpieza del arnes. Conflicto del verificador instalado resuelto conservando sus
comprobaciones nuevas y agregando CLI como seccion 8; lista de paquetes en 9.
La ISO bba02034... sigue siendo evidencia de la base anterior. Falta reconstruir.

## ISO actualizada sobre main 42031e1 (9-nov UTC)

Construccion completa con espejo y epoch 1794186923; cambios locales del PR-B.
SHA-256: 243769073218934f7813cb8c10978a401937fdcbe5101e3b5305c6509f8cbe9f.
Tamanio: 481296384 bytes.
El usuario ejecuto el inspector sobre esta ISO: resultado OK. CLI 0.1.0-1,
manual comprobado por el inspector, ayuda general y verify disponibles;
repo temporal sin restos en root/packages, fuentes y listas de APT; pool
persistente de 30 paquetes sin nimbo-audit ni backports. Unico backport
instalado en live: calamares 3.3.8-1~bpo12+1.
Hash y logs 0180, 0200 y auditoria 0210 comprobados desde el host.

Pendiente para el commit publicado: MATCH en CI y pruebas QEMU live/instalado,
hermetismo y RAM con el equipo revisor. La prueba de ayuda no sustituye un caso
funcional completo de init/capture/verify en la sesion live o instalada.
Esta medicion corresponde a cambios locales; el epoch del commit final sera otro.
