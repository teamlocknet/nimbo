# ADR-002 — Orden determinista de empaquetado del squashfs (sortfile completo)

**Estado:** Aceptado

## Contexto

Tras fijar la compresión a single-thread ([ADR-001](ADR-001-compresion-determinista-squashfs.md)),
el arnés (`repro/build-twice.sh` + `diff-isos.sh`) midió que **dos compilaciones del mismo
commit siguen difiriendo** (~12 bytes en `live/filesystem.squashfs`, en cascada a
`sha256sum.txt`). El diagnóstico con diffoscope, **verificado byte a byte**, aisló la causa:

- En el superbloque squashfs, **todas** las tablas (`bytes_used`, `id_table`, `inode_table`,
  `directory_table`, `fragment_table`, `lookup_table`) aparecen **corridas exactamente 12
  bytes** entre A y B, y un bloque de la **sección de datos** (~64 MB) difiere con SHA
  distinto. Es decir: la sección de **datos comprimidos** cambia de tamaño y contenido → los
  ficheros se **empaquetan en orden distinto**.
- `unsquashfs -lls` (archivos, orden lógico, permisos, mtimes) coincide byte a byte: eso
  ocurre porque el **formato on-disk de squashfs ordena siempre la tabla de directorios**.
  Lo que NO se ordena es el **orden físico de escritura de los datos**, que sigue el **orden
  de scan (`readdir`)** del árbol — **no determinista entre dos `debootstrap`** (el orden de
  entradas en el sistema de ficheros del host varía).

Investigación de la vía limpia (leída del fuente, no de memoria):

- `squashfs-tools 4.5.1` (`sort.c`): los ficheros **listados** en el fichero de `-sort` se
  empaquetan en un orden derivado de ese fichero (determinista); los **no listados** caen a
  prioridad 0 en **orden de scan** (readdir, no determinista). Para MATCH hay que listar
  **todos** los ficheros regulares del rootfs.
- `live-build 20230502` (`scripts/build/binary_rootfs`): **soporta `-sort` de forma nativa** —
  si existe `config/rootfs/squashfs.sort`, lo referencia con `-sort squashfs.sort` en la
  invocación de `mksquashfs`. Es el punto de extensión oficial, **sin parches ni wrappers**.
- **El sortfile NO queda dentro de la ISO** en nuestra config (default `LB_BUILD_WITH_CHROOT=true`),
  verificado en el fuente: `binary_chroot` mueve el rootfs real al **anidado `chroot/chroot`**
  (`mv chroot chroot.tmp` → `mv chroot.tmp chroot/chroot`), y `binary_rootfs` empaqueta ese
  anidado vía `Chroot chroot "mksquashfs chroot …"`, mientras que copia `squashfs.sort` al
  `chroot` **externo** (`cp -a config/rootfs/squashfs.sort chroot`) — un nivel **por encima**
  del árbol empaquetado. Es decir, el sortfile vive **fuera** del árbol que se comprime, así
  que **no aparece en la imagen** y **no hace falta `excludes`** para limpiarlo.

El sortfile **no puede ser estático**: la lista exacta de ficheros la produce `debootstrap`
y cambia. Debe **generarse en build-time** desde el `chroot/` real.

## Decisión

Forzar orden determinista de empaquetado por la **vía nativa de live-build**:

1. **Generar `config/rootfs/squashfs.sort` en build-time**, dentro de `iso/live-build/auto/build`,
   partiendo `lb build` en sus etapas nativas (`bootstrap → chroot → [generar sortfile] →
   installer → binary`). El sortfile lista **todos** los ficheros regulares del `chroot/` con
   prioridad 0, en orden estable de bytes:
   `find chroot -xdev -type f -printf '%p 0\n' | LC_ALL=C sort`.
   Con la lista **completa**, el orden de empaquetado deja de depender de `readdir` y pasa a
   ser el del sortfile (determinista). Se hace **dentro de `auto/build`** para preservar el
   `MKSQUASHFS_OPTIONS="-processors 1 …"` de ADR-001, que ese script exporta.
2. **Guard fail-loud:** si algún fichero del rootfs tiene un **espacio en el nombre**, abortar
   el build. El formato del sortfile (`ruta prioridad`, separado por espacios) no soporta
   espacios; un fichero así rompería silenciosamente el orden. Preferimos fallar ruidoso a
   perder determinismo en silencio (determinismo primero).
**No se añade `excludes`:** en la config actual (`LB_BUILD_WITH_CHROOT=true`) el sortfile queda
**fuera** del árbol empaquetado (ver Contexto), así que no ensucia la ISO y un `excludes`
sería un no-op. Se mantiene la superficie mínima. **Nota para el futuro:** si algún día se
usara `LB_BUILD_WITH_CHROOT=false`, `mksquashfs` empaqueta directamente `chroot/` con el
sortfile copiado a su lado; **habría que revisar** si `squashfs.sort` cae dentro del árbol y,
de ser así, añadir `config/rootfs/excludes` con `squashfs.sort`.

`config/` está en `.gitignore` (lo regenera `lb config`): el sortfile no se commitea; se
genera solo en cada build. El cambio versionado es sólo `auto/build`.

## Consecuencias

- **Cierra la causa de orden de empaquetado**: el objetivo es pasar de DIFFER a **MATCH**
  (dos builds del mismo commit → SHA-256 idéntico). Se verifica con los ojos con el arnés
  (`build-twice.sh` + `diff-isos.sh`).
- **Producto limpio sin piezas extra**: `/squashfs.sort` **no** queda dentro de la imagen —
  no por un `excludes`, sino porque en `with_chroot=true` el sortfile vive fuera del árbol
  empaquetado (ver Contexto). Menos superficie que mantener.
- **Coste**: `auto/build` deja de ser un único `lb build` y pasa a orquestar las etapas; y se
  recorre el árbol una vez (`find`) para generar el sortfile — despreciable frente al build.
- **Robustez / límite conocido**: nombres de fichero con **espacios** abortan el build
  (guard). En un bookworm mínimo (solo `main`, sin escritorio ni recommends) no se esperan;
  si en el futuro un paquete los introduce, se decidirá el escape en una vuelta aparte.
- **Reversible**: si una versión futura de `mksquashfs`/live-build ordena el scan de forma
  determinista por defecto, se puede retirar el sortfile con un ADR que reemplace a éste.
- **Coherencia**: parte de la terna del squashfs reproducible —
  [ADR-001](ADR-001-compresion-determinista-squashfs.md) (compresión multihilo) · ADR-002
  (orden de empaquetado) · [ADR-003](ADR-003-cache-apt-determinista-squashfs.md) (caché APT,
  la causa que este ADR dejó al descubierto). Juntos buscan el bit-idéntico local; ninguno
  mete todavía la comparación al CI (vuelta futura).

## Fecha

2026-09-04
