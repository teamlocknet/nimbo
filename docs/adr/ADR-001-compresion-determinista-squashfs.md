# ADR-001 — Compresión determinista del squashfs (mksquashfs single-thread)

**Estado:** Aceptado

## Contexto

El arnés de reproducibilidad (Paso 1C.1, `repro/build-twice.sh` + `diff-isos.sh`) midió
que **dos compilaciones de la ISO del mismo commit**, con el mismo `SOURCE_DATE_EPOCH`,
**difieren**. El diagnóstico con diffoscope aisló la causa a una **única** fuente:

- Solo cambian `live/filesystem.squashfs` (~4 bytes de tamaño) y, en cascada, `sha256sum.txt`.
- El contenido del squashfs es idéntico: `unsquashfs -lls` (archivos, orden, permisos,
  **mtimes**) coincide byte a byte, y el `Creation time` del superbloque es el mismo
  (`SOURCE_DATE_EPOCH` ya lo fija).
- Lo único que varía son los **bytes comprimidos**. Causa: la **compresión xz multihilo**
  de `mksquashfs` no es determinista — el ensamblado de bloques/fragmentos depende del
  scheduling de hilos (la máquina de build tiene 12 cores).

Se verificó que **no existe un modo paralelo-determinista robusto** en `mksquashfs`
(squashfs-tools no ofrece "paralelo reproducible"), y que live-build **no** tiene un flag de
`lb config` para el número de procesadores. Sí expone la variable de entorno
`MKSQUASHFS_OPTIONS`, que `binary_rootfs` **anexa** a la invocación de `mksquashfs` — su
punto de extensión oficial, sin parches ni hacks.

## Decisión

Fijar la compresión del squashfs a **single-thread** con **`-processors 1`**, aplicado por
la vía limpia: `export MKSQUASHFS_OPTIONS="-processors 1 …"` en
`iso/live-build/auto/build`. Aplica a **todos** los builds (local y CI): la reproducibilidad
pasa a ser el comportamiento por defecto del proyecto. Se prefiere lo **correcto/reproducible
sobre lo rápido**; en CI el tiempo de build no es crítico.

## Consecuencias

- **Elimina el no-determinismo por multihilo**: se verificó en el build (`Parallel
  mksquashfs: Using 1 processor`) y que mksquashfs single-thread es **determinista dada una
  entrada fija** (re-empaquetar el mismo árbol dos veces → SHA idéntico).
- **Coste: build más lento** en la etapa de squashfs (1 hilo en vez de 12).
  **Impacto medido in-situ (misma máquina, 12 cores):**
  - Etapa squashfs (`lb binary_rootfs`, single-thread): **≈ 1m37s**.
  - Build completo: **≈ 5m50s por build** (11m41s los dos builds del arnés).
  - Margen frente al `timeout-minutes: 40` de la CI (1B): **enorme** (~5m50 ≪ 40m). Si en
    el futuro se acercara, se sube el timeout en una vuelta aparte (no en este ADR).
- **NO logra MATCH por sí solo — queda un residual (→ 1C.3):** tras fijar single-thread, dos
  builds del mismo commit **siguen difiriendo** (~12 bytes en el squashfs). Diagnóstico: el
  contenido, mtimes, permisos y orden lógico (`unsquashfs -lls`) son idénticos y el contenido
  de los archivos es byte a byte igual; la diferencia es el **orden de readdir** con que
  mksquashfs empaqueta los directorios, no determinista entre dos `debootstrap`. Se descartó
  la tabla de export NFS (`-no-exports` no lo arregla). **Este ADR cierra la causa multihilo;
  el orden de empaquetado es la siguiente maratoncita (1C.3).**
- **Reversible:** si aparece un modo `mksquashfs` paralelo-determinista sólido, se puede
  volver a paralelo ajustando la misma variable, con un ADR que reemplace a este.

## Fecha

2026-09-04
