# ADR-007 — initrd generado sobre tmpfs (independencia del sistema de archivos del anfitrión)

**Estado:** Aceptado

## Contexto

La compuerta `repro-verify` (ADR-004) demostraba reproducibilidad entre dos compilaciones
en runners de GitHub con `boot_id` distinto, pero siempre sobre el **mismo tipo de
anfitrión** (VM de GitHub, ext4). El 23-oct-2026, al compilar el mismo commit (`a4af6b8`,
mismo `SOURCE_DATE_EPOCH=1791342616`, misma imagen por digest, mismo snapshot) en una
máquina física distinta con **btrfs**, la ISO salió distinta:

- CI (familia ext — `stat -f` informa `ext2/ext3`; cuatro compilaciones): `17ee64c8624d15416c4996e82585b235e187cc045313176f19cc0b8e049f1da0`
- Portátil (btrfs): `41d97860cd568351e0b714de77fc5db7882ecb85fd29a75c76f452bd05333a9d`

El diagnóstico (detalle en [H-001](../hallazgos/H-001-filtracion-nlink-btrfs.md)) aisló una
**única** causa: de 555 ficheros de la ISO solo difieren el initrd y el squashfs que lo
contiene; dentro del initrd el contenido es idéntico y lo único distinto es el **número de
enlaces (`nlink`) de los 332 directorios**: 2 + subdirectorios en CI, 1 en btrfs.

Mecanismo, comprobado en el código de bookworm:

- `mkinitramfs` (initramfs-tools 0.142) arma el initrd en
  `mktemp -d ${TMPDIR:-/var/tmp}/mkinitramfs_XXXXXX` y lo empaqueta en cpio `newc`, formato
  que **guarda `nlink`**.
- El chroot de live-build vive en el directorio de build del anfitrión (bind mount), así
  que `/var/tmp` hereda su sistema de archivos. ext4 y tmpfs cuentan los enlaces de un
  directorio como 2 + subdirectorios; btrfs devuelve siempre 1.
- `mksquashfs` calcula por su cuenta los enlaces de los directorios, por eso el resto del
  squashfs no se veía afectado.

Alternativas consideradas:

- **A — tmpfs solo para el espacio temporal del initrd (elegida).** Cambio mínimo, ataca la
  causa.
- **B — todo el árbol de build en un volumen del contenedor.** Cierra la clase entera de
  filtraciones del sistema de archivos, pero es invasiva (RAM/disco, receta) con el
  calendario actual. Descartada por ahora, no por mala.
- **C — fallar el build en btrfs.** No arregla nada y bloquearía builds correctos en
  Fedora/openSUSE/Omarchy. Se adopta solo como **aviso**.

## Decisión

1. **Hook `config/hooks/normal/9990-nimbo-initrd-tmpfs.hook.chroot`.** Corre el último de
   los hooks y antes de `chroot_hacks`, dentro del chroot. Monta un tmpfs **encima** de
   `/var/tmp`, ejecuta `update-initramfs -k all -t -u` (el mismo comando que ejecutaría
   `chroot_hacks` de live-build 20230502), desmonta y crea
   `/initrd.img_has_already_been_regenerated`, el marcador con el que live-build **omite**
   regenerar el initrd en `chroot_hacks` y que **borra él mismo** a continuación.
2. **Auto-chequeo en el mismo hook:** si algún directorio del initrd tiene `nlink=1`, el
   build **falla**. En ext4 o tmpfs un directorio tiene siempre ≥ 2, así que la guarda
   detecta la filtración en cualquier sistema de archivos del anfitrión, no solo en btrfs.
3. **Aviso en `build-in-container.sh`:** la cabecera del build muestra el sistema de
   archivos del directorio de build y, si es btrfs, un aviso visible que remite a comparar
   el SHA-256 con el de CI. Avisa, no bloquea.

## Sin rastro en la imagen

El hook no puede dejar huella en lo que se distribuye. Por construcción:

- **Punto de montaje:** el tmpfs se monta sobre `/var/tmp`, que ya existe; no se crea ni
  se borra ninguna entrada en el directorio padre, así que no cambia ningún mtime. Se
  desmonta antes de salir (con `trap`) y el hook falla si `/var/tmp` siguiera montado.
- **Contenido temporal:** todo lo que `mkinitramfs` escribe vive en el tmpfs y desaparece
  con él; el `/var/tmp` real queda intacto.
- **Marcador:** `chroot_hacks` lo borra (`rm -f chroot/initrd.img_has_already_been_regenerated`,
  línea 77 de live-build 20230502) antes de que exista el squashfs.

**Prueba empírica:** compilada en el PC con btrfs **con** el hook y con `SOURCE_DATE_EPOCH` forzado al del
commit de referencia, la ISO es **bit a bit idéntica** a la de CI:
`17ee64c8624d15416c4996e82585b235e187cc045313176f19cc0b8e049f1da0`, confirmado además con
`cmp`. Como el SHA-256 cubre la imagen entera, eso prueba a la vez que la filtración está
cerrada y que el hook **no deja ningún rastro**: ni el punto de montaje, ni mtimes tocados,
ni el marcador. Evidencia formal en
[`repro/evidencia/2026-10-23-match-entre-anfitriones.md`](../../repro/evidencia/2026-10-23-match-entre-anfitriones.md).

## Consecuencias

- La ISO deja de depender del sistema de archivos del anfitrión en el único campo
  observado. La reproducibilidad pasa de "entre runners de GitHub (`boot_id`)" a
  "entre máquinas físicas distintas con sistemas de archivos distintos".
- Una filtración del mismo tipo en el initrd ya no puede pasar en silencio: el build falla.
- Otras filtraciones del anfitrión en **otros** campos no quedan cubiertas por este hook;
  el juez sigue siendo comparar el SHA-256 entre anfitriones distintos (y diffoscope si
  difiere). La alternativa B queda como mejora futura.
- Coste: ninguno en tiempo de build (el initrd se genera el mismo número de veces: el
  hook sustituye a la generación de `chroot_hacks`).
- Mantenimiento: si se sube live-build, comprobar que `chroot_hacks` sigue honrando el
  marcador y que el comando de regeneración no cambió.

## Fecha

2026-10-23
