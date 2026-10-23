# H-001 — La máquina que compila se colaba en la ISO: una filtración del anfitrión, localizada y cerrada

**Fecha:** 2026-10-23 · **Estado:** cerrado · **Decisión asociada:** [ADR-007](../adr/ADR-007-initrd-sobre-tmpfs.md)
**Requisito afectado:** RNF-SEC-07 (reproducibilidad bit a bit)

## 1. Por qué importa

Una compilación es **reproducible** si cualquiera, con el mismo código fuente, obtiene
exactamente el mismo fichero, bit a bit. Es lo que permite a un tercero comprobar que la ISO
publicada sale de este código y de nada más: compila, calcula el SHA-256 y compara.

Hasta este hallazgo, el proyecto lo demostraba con una compuerta de CI que compila la ISO
**dos veces en dos máquinas virtuales distintas de GitHub** y exige el mismo SHA-256. La
objeción razonable era: *"esas dos máquinas son del mismo tipo; lo único probado es que
arrancaron por separado (`boot_id` distinto)"*. Este documento responde a esa objeción con
un experimento real, y muestra algo más valioso: **el proceso de verificación detectó una
filtración auténtica del anfitrión** que dos máquinas iguales nunca habrían revelado.

## 2. Qué se comparó

El mismo commit (`a4af6b8`) compilado en dos anfitriones distintos, con todo lo demás fijado:

| | CI (GitHub Actions) | Portátil del equipo |
|---|---|---|
| Máquina | VM efímera de GitHub, Ubuntu 24.04 | PC físico, Arch Linux (Omarchy), kernel 7.2.5 |
| Sistema de archivos del build | ext4 | **btrfs** |
| Contenedor | `debian:bookworm-slim` por digest `88200866…4171` | el mismo |
| Paquetes | snapshot.debian.org `20260901T000000Z` | el mismo |
| `SOURCE_DATE_EPOCH` | 1791342616 | el mismo |
| **SHA-256 de la ISO** | `17ee64c8…1da0` (4 compilaciones, 7 y 23-oct) | `41d97860…333a9d` |

Mismo código, mismas herramientas, mismos paquetes, misma hora congelada: **ISO distinta**.

## 3. Cómo se localizó (de lo grueso a lo fino)

Ninguna conclusión se sacó de un resumen; cada paso se comprobó sobre los ficheros reales.

1. **La ISO entera.** Los SHA-256 difieren. Se volvió a compilar en CI para tener la ISO de
   referencia (los artefactos de CI caducan a los 7 días) y dio otra vez `17ee64c8…`.
2. **Los 555 ficheros de la ISO.** Se calculó el SHA-256 de cada uno. Solo difieren **dos**:
   `live/filesystem.squashfs` (el sistema completo) y `live/initrd.img` (el disco de arranque
   inicial). El kernel, el gestor de arranque, shim y todo lo demás son idénticos.
3. **Dentro del squashfs** (diffoscope + `unsquashfs -lls`). El único fichero distinto es
   `/boot/initrd.img-6.1.0-52-amd64`: el mismo initrd del punto anterior, que también viaja
   dentro del sistema. El problema queda reducido al initrd.
4. **Dentro del initrd.** Se desempaquetaron los dos: **1156 ficheros con contenido idéntico**
   (mismos nombres, mismos SHA-256). La diferencia está en los metadatos: en el listado
   detallado difieren 332 líneas, **todas directorios**, y en **una sola columna**: el número
   de enlaces (`nlink`). Quitando esa columna, los listados son idénticos en permisos,
   dueño, tamaño, fecha y orden.

| Directorio del initrd | `nlink` en CI | `nlink` en el portátil |
|---|---|---|
| `.` | 7 | 1 |
| `conf` | 3 | 1 |
| `conf/conf.d` | 2 | 1 |
| `etc` | 6 | 1 |
| `etc/live` | 3 | 1 |
| … (332 directorios) | 2 + nº de subdirectorios | 1 |

## 4. El mecanismo

- **Qué es `nlink`.** Cada fichero o directorio lleva un contador de enlaces. En los
  sistemas de archivos clásicos de Linux (ext4) un directorio vale **2 + su número de
  subdirectorios** (su propio nombre, su entrada `.` y la entrada `..` de cada hijo).
  **btrfs** no sigue esa convención: devuelve **1** para todo directorio.
- **Por qué acaba en la ISO.** El initrd lo genera `mkinitramfs`, que copia los ficheros a
  un directorio temporal (`/var/tmp/mkinitramfs_XXXXXX`) y lo empaqueta en formato
  **cpio "newc"**, que **guarda `nlink` de cada entrada**.
- **Por qué depende de la máquina.** La compilación ocurre en un contenedor, pero el árbol
  de trabajo (el "chroot" donde se instala el sistema) vive en una carpeta del anfitrión
  montada dentro. Así, `/var/tmp` del chroot está físicamente en el disco del anfitrión y
  hereda **su** sistema de archivos: ext4 en GitHub, btrfs en el portátil.
- **Por qué solo el initrd.** La herramienta que crea el squashfs (`mksquashfs`) calcula
  ella misma los enlaces de los directorios en lugar de leerlos del disco; cpio no.

Se comprobó aparte, con un árbol de prueba: el mismo directorio da en **tmpfs** exactamente
los valores de CI (`.`=7, `conf`=3, `conf/conf.d`=2, `etc`=6, `etc/live`=3,
`etc/live/boot`=2) y en btrfs, 1 en todos.

## 5. El arreglo

Un paso de construcción (hook) genera el initrd final con `/var/tmp` sobre **tmpfs**, un
sistema de archivos en memoria que cuenta los enlaces igual que ext4 en **cualquier**
anfitrión. Además, ese paso **comprueba** el resultado: si algún directorio del initrd
tiene `nlink=1`, la compilación **falla**. Esa comprobación protege en cualquier sistema de
archivos, no solo en btrfs. Y la cabecera del build avisa cuando se compila sobre btrfs.
Detalle técnico y alternativas descartadas en [ADR-007](../adr/ADR-007-initrd-sobre-tmpfs.md).

## 6. La prueba de que quedó cerrado

El criterio se fijó **antes** de probar el arreglo y sin margen de interpretación: compilar
en el portátil con btrfs y obtener **exactamente** el SHA-256 de CI. Para que el arreglo fuera
la única diferencia, se forzó el mismo `SOURCE_DATE_EPOCH` del commit de referencia.

```
P: [hook]   /boot/initrd.img-6.1.0-52-amd64: 0 directorios con nlink=1 (OK)
17ee64c8624d15416c4996e82585b235e187cc045313176f19cc0b8e049f1da0  live-image-amd64.hybrid.iso
cmp: IDÉNTICAS byte a byte
```

| Compilación | Sistema de archivos | SHA-256 |
|---|---|---|
| CI, 4 veces (7 y 23-oct) | ext4 | `17ee64c8…1da0` |
| Portátil, sin arreglo | btrfs | `41d97860…333a9d` |
| **Portátil, con arreglo** | **btrfs** | **`17ee64c8…1da0`** |

La ISO completa (475 004 928 bytes) es idéntica byte a byte. Como el SHA-256 cubre toda la
imagen, esto prueba también que el arreglo no deja ningún rastro en ella. Detalle del
anfitrión, comando y salida en
[`repro/evidencia/2026-10-23-match-entre-anfitriones.md`](../../repro/evidencia/2026-10-23-match-entre-anfitriones.md).

## 7. Qué demuestra (para la sustentación)

- **La independencia ya no descansa solo en `boot_id`.** La misma ISO, bit a bit, sale de
  una VM de GitHub con ext4 y de un PC físico con btrfs, otro sistema operativo anfitrión
  y otro kernel.
- **La verificación funciona de verdad.** No es una ceremonia que siempre da verde: cuando
  el anfitrión cambió, detectó la diferencia, y el método (comparar, bajar de nivel,
  comprobar sobre los ficheros reales) la localizó hasta un único campo de un único
  formato.
- **El arreglo es mínimo y verificable:** una sola causa, un solo cambio, y el criterio de
  éxito fijado de antemano (el SHA-256 exacto de CI), sin margen de interpretación.

## 8. Nota de honestidad

La ISO del Paso 3C.1 que se midió en la máquina anterior del equipo (Fedora,
`c8873cdb…d037`) **probablemente nunca coincidió** con la de CI de ese mismo cambio
(`9ff98ece…`). Es **consistente** con esta misma causa —Fedora usa btrfs por defecto—, pero
**no está probado**: esa ISO ya no existe y no se puede comparar. En su momento la diferencia
no se investigó porque nadie comparó una ISO local con la de CI. Desde este hallazgo, esa
comparación es parte del procedimiento.

## Evidencia

- Informe diffoscope: `repro/out/reporte-diffoscope.{html,txt}` (generado con
  `repro/diff-isos.sh`, no versionado por tamaño).
- Ejecuciones de CI: `build-iso` run `37565498007` (intentos 1 y 2), `repro-verify` run
  `37565498016`.
- Código revisado: `mkinitramfs` de initramfs-tools 0.142+deb12u3 (líneas 281–286) y
  `chroot_hacks` / `functions/chroot.sh` de live-build 20230502, ambos del snapshot anclado.
