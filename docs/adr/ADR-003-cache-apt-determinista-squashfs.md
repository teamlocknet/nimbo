# ADR-003 — Caché binario de APT determinista (desactivarlo en la imagen)

**Estado:** Aceptado

## Contexto

Tras cerrar la compresión ([ADR-001](ADR-001-compresion-determinista-squashfs.md)) y el
orden de empaquetado ([ADR-002](ADR-002-orden-determinista-empaquetado-squashfs.md)), el
arnés seguía en **DIFFER** por ~12 bytes en `live/filesystem.squashfs`. Al comparar el
**contenido fichero a fichero** de los dos árboles descomprimidos (no sólo `unsquashfs -lls`,
que sólo cubre nombre/tamaño/mtime/permisos), de **12 708** ficheros regulares **sólo 2**
difieren, con **tamaño idéntico** pero **contenido distinto**:

- `/var/cache/apt/pkgcache.bin` (1 824 283 B)
- `/var/cache/apt/srcpkgcache.bin` (1 594 372 B)

Son los **cachés binarios de APT**: APT los **reserializa en cada invocación** y su contenido
no es determinista (estructuras internas/mmap; no lo cubre `SOURCE_DATE_EPOCH`). Estaban
**enmascarados** por el no-determinismo de orden; al fijarlo (ADR-002) quedaron expuestos
como la última causa.

Punto clave verificado en el fuente de live-build: **un `rm` no basta**. La etapa `binary`
vuelve a correr APT dentro del chroot anidado (`binary_rootfs` instala `squashfs-tools` ahí
justo antes de empaquetar, y luego `binary_zsync`, etc.), lo que **regenera** los `.bin`
antes del `mksquashfs`. Hay que **impedir que APT los escriba**, no sólo borrarlos.

## Decisión

Desactivar el caché binario de APT por configuración, en `iso/live-build/auto/build`, tras
`lb chroot` y antes de empaquetar: escribir `etc/apt/apt.conf.d/99nimbo-reproducible` en el
chroot con

```
Dir::Cache::pkgcache "";
Dir::Cache::srcpkgcache "";
```

y borrar los `.bin` ya existentes. Con el caché desactivado, APT **no escribe** los `.bin`
en **ninguna** invocación (el chroot anidado hereda este `apt.conf.d`), así que no hay
fichero no determinista que empaquetar. El snippet se genera en build-time (no se commitea:
`config/` está en `.gitignore`) y **queda en la imagen** (es config de APT del sistema).

## Consecuencias

- **Elimina la última causa medida** de no-reproducibilidad del squashfs: junto con ADR-001
  (compresión) y ADR-002 (orden), el objetivo es **MATCH** (dos builds del mismo commit →
  SHA-256 idéntico), verificado con los ojos con el arnés.
- **Efecto en runtime**: APT no mantiene un caché binario persistente en la imagen; reconstruye
  en memoria en cada corrida. Coste despreciable y aceptable para un SO de auditoría
  air-gapped (menos estado mutable en `/var/cache`).
- **Superficie mínima**: un snippet de 2 líneas; sin hooks ni includes nuevos. Vive en el
  mismo `auto/build` que ya orquesta las etapas.
- **Reversible**: quitar el snippet restaura el caché por defecto (a costa de la
  reproducibilidad).
- **Coherencia**: cierra la terna de causas del squashfs reproducible —
  [ADR-001](ADR-001-compresion-determinista-squashfs.md) (compresión) ·
  [ADR-002](ADR-002-orden-determinista-empaquetado-squashfs.md) (orden) · ADR-003 (caché APT).
  Ninguno mete todavía la comparación al CI (vuelta futura, cuando el MATCH local sea estable).

## Fecha

2026-09-05
