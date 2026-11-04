# H-001 — Nuestra verificación de reproducibilidad funciona: detectó una filtración real del anfitrión, la localizó hasta un campo y la cerró

**Fecha:** 2026-10-23 · **Estado:** cerrado · **Decisión asociada:** [ADR-007](../adr/ADR-007-initrd-sobre-tmpfs.md)
**Requisito:** RNF-SEC-07 (reproducibilidad bit a bit)

## En una frase

Cambiamos de verdad la máquina que compila la ISO; la verificación **detectó** que el
resultado ya no era idéntico, el método **localizó** la causa hasta un único campo de un
único formato de archivo, y el arreglo la **cerró** con un criterio de éxito fijado de
antemano: el mismo SHA-256, bit a bit, que en CI.

## 1. La afirmación y la objeción

Una compilación es **reproducible** si cualquiera, con el mismo código fuente, obtiene
exactamente el mismo fichero. Es lo que permite a un tercero comprobar que la ISO publicada
sale de este código y de nada más: compila, calcula el SHA-256 y compara.

El proyecto lo demostraba con una compuerta de CI (ADR-004) que compila la ISO **dos veces
en dos máquinas virtuales de GitHub** y exige el mismo SHA-256. La objeción que teníamos
anotada era legítima: *esas dos máquinas son del mismo tipo (misma imagen, mismo sistema de
archivos); lo único probado es que arrancaron por separado (`boot_id` distinto)*. Una
verificación que compara dos copias del mismo entorno puede dar siempre verde sin haber
puesto nada a prueba.

Para responderla no basta con argumentar: hay que **cambiar el anfitrión** y ver si la
verificación se entera.

## 2. El experimento: otro anfitrión, todo lo demás fijado

El mismo commit (`a4af6b8`) compilado en un anfitrión deliberadamente distinto:

| | CI (GitHub Actions) | PC del equipo |
|---|---|---|
| Máquina | VM efímera de GitHub | PC físico (portátil), Intel Core i7-1355U |
| Sistema operativo anfitrión | Ubuntu 24.04 | Omarchy (Arch Linux), kernel 7.2.5 |
| Sistema de archivos del build | familia ext¹ | **btrfs** |
| Contenedor | `debian:bookworm-slim` por digest `88200866…4171` | el mismo |
| Paquetes | snapshot.debian.org `20260901T000000Z` | el mismo |
| `SOURCE_DATE_EPOCH` | 1791342616 | el mismo |

¹ Medido en el log de CI: `stat -f` informa `ext2/ext3`, que es el número mágico `0xEF53`
compartido por ext2, ext3 y ext4; `stat` no puede distinguirlos. En la práctica es ext4,
pero lo medido es "familia ext".

## 3. Lo que la verificación detectó

| | SHA-256 de la ISO |
|---|---|
| CI (4 compilaciones: 7-oct ×3, 23-oct ×1) | `17ee64c8624d15416c4996e82585b235e187cc045313176f19cc0b8e049f1da0` |
| PC con btrfs | `41d97860cd568351e0b714de77fc5db7882ecb85fd29a75c76f452bd05333a9d` |

Mismo código, mismas herramientas, mismos paquetes, misma hora congelada: **ISO distinta**.
La verificación no dio verde por inercia: el cambio de anfitrión se notó en el resultado.

La regla que seguimos en ese momento fue **no tocar nada** (ni la receta ni el build) hasta
saber exactamente qué difería.

## 4. Cómo se localizó, de lo grueso a lo fino

Ninguna conclusión se sacó de un resumen; cada paso se comprobó sobre los ficheros reales.

1. **La ISO entera.** Los SHA-256 difieren. Como los artefactos de CI caducan a los 7 días,
   se volvió a compilar en CI para tener la ISO de referencia: dio otra vez `17ee64c8…`,
   16 días después de la primera vez.
2. **Los 555 ficheros de la ISO.** Se calculó el SHA-256 de cada uno. Solo difieren **dos**:
   `live/filesystem.squashfs` (el sistema completo) y `live/initrd.img` (el disco de arranque
   inicial), más `sha256sum.txt`, que solo lista los hashes de los otros. El kernel, el gestor
   de arranque, shim y todo lo demás son idénticos.
3. **Dentro del squashfs** (diffoscope + `unsquashfs -lls`). El único fichero distinto es
   `/boot/initrd.img-6.1.0-52-amd64`: el mismo initrd del punto anterior, que también viaja
   dentro del sistema. El problema queda reducido al initrd.
4. **Dentro del initrd.** Se desempaquetaron los dos: **1156 ficheros con contenido idéntico**
   (mismos nombres, mismos SHA-256). La diferencia está en los metadatos: en el listado
   detallado difieren 332 líneas, **todas directorios**, y en **una sola columna**: el número
   de enlaces (`nlink`). Quitando esa columna, los listados coinciden en permisos, dueño,
   tamaño, fecha y orden.

| Directorio del initrd | `nlink` en CI | `nlink` en el PC con btrfs |
|---|---|---|
| `.` | 7 | 1 |
| `conf` | 3 | 1 |
| `conf/conf.d` | 2 | 1 |
| `etc` | 6 | 1 |
| `etc/live` | 3 | 1 |
| … (332 directorios) | 2 + nº de subdirectorios | 1 |

De una ISO de 475 MB a **un campo numérico de 332 entradas de un archivo cpio**.

## 5. El mecanismo

- **Qué es `nlink`.** Cada fichero o directorio lleva un contador de enlaces. En la familia
  ext (y en tmpfs) un directorio vale **2 + su número de subdirectorios**: su propio nombre,
  su entrada `.` y la entrada `..` de cada hijo. **btrfs** no sigue esa convención y devuelve
  **1** para todo directorio.
- **Por qué acaba en la ISO.** El initrd lo genera `mkinitramfs`, que copia los ficheros a
  un directorio temporal (`/var/tmp/mkinitramfs_XXXXXX`) y lo empaqueta en formato
  **cpio "newc"**, que **guarda `nlink` de cada entrada**.
- **Por qué depende de la máquina.** La compilación ocurre en un contenedor, pero el árbol
  de trabajo (el "chroot" donde se instala el sistema) vive en una carpeta del anfitrión
  montada dentro. `/var/tmp` del chroot está físicamente en el disco del anfitrión y hereda
  **su** sistema de archivos.
- **Por qué solo el initrd.** La herramienta que crea el squashfs (`mksquashfs`) calcula
  ella misma los enlaces de los directorios en lugar de leerlos del disco; cpio no.

El mecanismo se comprobó aparte, no solo se dedujo: el mismo árbol de directorios da en
**tmpfs** exactamente los valores de CI (`.`=7, `conf`=3, `conf/conf.d`=2, `etc`=6,
`etc/live`=3, `etc/live/boot`=2) y en btrfs, 1 en todos. Y el código de `mkinitramfs` de
bookworm (initramfs-tools 0.142, líneas 281–286) confirma dónde arma el árbol temporal.

## 6. El cierre, con el criterio fijado antes de probar

**Arreglo** ([ADR-007](../adr/ADR-007-initrd-sobre-tmpfs.md)): un paso de construcción
genera el initrd final con `/var/tmp` sobre **tmpfs**, que cuenta los enlaces como la familia
ext en **cualquier** anfitrión. Ese mismo paso **comprueba** el resultado: si algún
directorio del initrd tiene `nlink=1`, la compilación **falla**, sea cual sea el sistema de
archivos del anfitrión. La cabecera del build, además, avisa cuando se compila sobre btrfs.

**Criterio de éxito, fijado antes de compilar y sin margen de interpretación:** en el PC con
btrfs, obtener **exactamente** el SHA-256 de CI. Para que el arreglo fuera la única
diferencia, se forzó el mismo `SOURCE_DATE_EPOCH` del commit de referencia.

```
P: [hook]   /boot/initrd.img-6.1.0-52-amd64: 0 directorios con nlink=1 (OK)
17ee64c8624d15416c4996e82585b235e187cc045313176f19cc0b8e049f1da0  live-image-amd64.hybrid.iso
cmp: IDÉNTICAS byte a byte
```

| Compilación | Sistema de archivos | SHA-256 |
|---|---|---|
| CI, 4 veces (7 y 23-oct) | familia ext | `17ee64c8…1da0` |
| PC, sin arreglo | btrfs | `41d97860…333a9d` |
| **PC, con arreglo** | **btrfs** | **`17ee64c8…1da0`** |

La ISO completa (475 004 928 bytes) es idéntica byte a byte. Como el SHA-256 cubre toda la
imagen, esto prueba a la vez que la filtración está cerrada y que el arreglo no deja ningún
rastro en ella. Y en el propio PR del arreglo (#27), la compuerta de CI sigue en verde con
el SHA nuevo (el commit cambia, así que cambia `SOURCE_DATE_EPOCH`): las dos patas
coinciden, con `boot_id` distintos y el auto-chequeo en verde en ambas. Detalle del
anfitrión, comando y salida en
[`repro/evidencia/2026-10-23-match-entre-anfitriones.md`](../../repro/evidencia/2026-10-23-match-entre-anfitriones.md).

## 7. Qué responde esto a la objeción del `boot_id`

- **La verificación pone a prueba algo real.** Cuando el anfitrión cambió, el resultado
  cambió y la comparación lo detectó. Una ceremonia que siempre da verde no habría visto
  nada.
- **El método llega a la causa.** Comparar, bajar de nivel y comprobar sobre los ficheros
  reales llevó de "la ISO es distinta" a "el campo `nlink` de 332 directorios de un cpio",
  sin suposiciones intermedias.
- **La independencia ya no descansa solo en `boot_id`.** La misma ISO, bit a bit, sale de
  una VM de GitHub con familia ext y de un PC físico con btrfs, otro sistema operativo
  anfitrión y otro kernel.
- **Y no puede volver en silencio.** El auto-chequeo del build falla si la misma filtración
  reaparece, en cualquier máquina.

## 8. Límites y nota de honestidad

- **Qué no cubre.** El arreglo cierra el único campo observado. Otra filtración del
  anfitrión en otro campo no la detectaría el auto-chequeo; la detectaría, como esta, la
  comparación del SHA-256 entre anfitriones distintos. Por eso esa comparación pasa a ser
  parte del procedimiento, no un experimento puntual. Y lo probado es "familia ext frente a
  btrfs"; otros sistemas de archivos (XFS, ZFS…) no se han medido.
- **La ISO de 3C.1.** La ISO del Paso 3C.1 que se midió en la máquina anterior del equipo
  (Fedora, `c8873cdb…d037`) **probablemente nunca coincidió** con la de CI de ese mismo
  cambio (`9ff98ece…`). Es **consistente** con esta causa —Fedora usa btrfs por defecto—,
  pero **no está probado**: esa ISO ya no existe y no se puede comparar. En su momento la
  diferencia no se investigó porque nadie comparó una ISO local con la de CI. Este hallazgo
  es, precisamente, el resultado de empezar a hacerlo.

## Evidencia

- Informe diffoscope: `repro/out/reporte-diffoscope.{html,txt}` (generado con
  `repro/diff-isos.sh`; no versionado por tamaño).
- Ejecuciones de CI: `build-iso` run `37565498007` (intentos 1 y 2), `repro-verify` runs
  `37565498016` (referencia), `39969425797` y `39971592206` (PR #27).
- Código revisado: `mkinitramfs` de initramfs-tools 0.142+deb12u3 (líneas 281–286) y
  `chroot_hacks` / `functions/chroot.sh` de live-build 20230502, ambos del snapshot anclado.
- Evidencia formal: [`repro/evidencia/2026-10-23-match-entre-anfitriones.md`](../../repro/evidencia/2026-10-23-match-entre-anfitriones.md).
