# H-004 — El SHA de la ISO dependía de la fecha de los ficheros en la copia de trabajo

**Fecha:** 2026-11-08 · **Estado:** cerrado (pendiente de merge) · **Decisión asociada:** ninguna nueva (arreglo de receta)
**Requisito:** RNF-SEC-07 (reproducibilidad bit a bit)

## En una frase

Al comprobar que el PR #36 no cambiaba la ISO, el mismo commit compilado con el mismo
`SOURCE_DATE_EPOCH` dio **un SHA en la copia de trabajo de Juan José y otro en un clon recién
hecho**; la causa eran las fechas de 36 entradas de `config/includes.chroot/`, que llegaban a
la ISO desde el disco del anfitrión. `auto/build` las fija ahora al epoch.

## 1. Qué se vio

Comprobación del PR #36 (método de H-001): compilar `2315e5c` con el epoch de `main`
(`SOURCE_DATE_EPOCH=1793814833`, 2026-11-04T17:53:53Z) y exigir el SHA de la ISO de CI de
`main`.

| Compilación | Dónde | SHA-256 |
|---|---|---|
| CI de `main` (`5fdec73`), run `42099008637` + compuerta `42099013154` (MATCH ×2) | GitHub Actions | `48c2e1c562f77371a5467cbd8fe959ad2a55b65e2f49881a5ac7331172189992` |
| `2315e5c` en la copia de trabajo | PC de Juan José (btrfs) | `b68343635576a1b636c8f544f2ea53d2e0cb06cbc39e72285ed228292e6542d3` ❌ |
| `2315e5c` en un clon recién hecho (`git clone --no-local`) | el mismo PC, mismo disco | `48c2e1c562f77371a5467cbd8fe959ad2a55b65e2f49881a5ac7331172189992` ✅ |

Mismo commit, mismo epoch, mismo anfitrión, mismo sistema de archivos. Lo único distinto
entre las dos últimas filas es **cuándo se escribieron los ficheros en el disco**.

## 2. Dónde estaba la diferencia

Las dos ISO miden lo mismo (475 004 928 bytes). Se extrajeron con `xorriso` y `unsquashfs`
dentro del contenedor bookworm anclado y se compararon:

- **Contenido:** idéntico. Los 34 261 ficheros del squashfs tienen el mismo SHA-256, y
  permisos, dueños, tamaños y rutas de las 40 564 entradas coinciden.
- **Fuera del squashfs:** solo cambia `sha256sum.txt` (el índice de hashes de la ISO, que
  incluye el squashfs).
- **Lo que cambia:** el **mtime** de 36 entradas, todas de `config/includes.chroot/`
  (`/etc/calamares/**`, `/usr/bin/nimbo-instalar`, `/usr/lib/live/config/01{50,60}-*` (en el
  repo bajo `lib/`, que bookworm fusiona en `/usr`),
  `/usr/lib/nimbo/calamares/**`, `/usr/share/applications/nimbo-instalar*.desktop` y sus
  carpetas). En CI todas valen `2026-11-04 17:53` (el epoch); en la copia de trabajo,
  `2026-10-23 11:36`, `2026-10-06 17:45` o `2026-11-04 16:13`, que es cuando Juan José
  escribió esos ficheros en su disco.

## 3. Por qué

`mksquashfs` 4.5.1 (el de bookworm en el snapshot anclado), en su `-help`:

> SOURCE_DATE_EPOCH — If set, this is used as the filesystem creation timestamp. Also any
> file timestamps which are **after** SOURCE_DATE_EPOCH will be clamped to SOURCE_DATE_EPOCH.

Recorta solo hacia abajo. live-build copia `config/includes.chroot/` al chroot conservando el
mtime, y ningún paso de la receta lo normalizaba (los hooks 0190 y 0200 solo fijan sus
propias carpetas). Entonces:

- **En CI** el checkout es siempre posterior al commit → fechas posteriores al epoch →
  recortadas al epoch. Por eso la compuerta MATCH ×2 nunca lo vio: las dos piernas tienen la
  misma condición.
- **En una copia de trabajo** los ficheros que no se han reescrito desde antes del commit
  tienen fechas anteriores al epoch → pasan tal cual a la ISO.

H-001 (23-oct) dio el SHA exacto de CI en este mismo PC porque, en ese momento, los ficheros
de la copia de trabajo eran posteriores al commit que se compiló. La reproducibilidad
afirmada entonces era correcta para ese árbol, pero dependía de una condición que nadie
había fijado.

## 4. El arreglo

`auto/build`, antes de la primera etapa de live-build:

```
find config -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} +
```

Todo `config/` (ficheros, carpetas y enlaces sin seguirlos) queda en el epoch. En CI esas
entradas ya acababan en el epoch, así que **la ISO de CI no cambia**. Se descartó
`mksquashfs -all-time`: fijaría la fecha de todo el sistema y cambiaría todos los SHA.

Test rojo → verde: `iso/live-build/tests/test-auto-build-mtimes.sh` (en el job de CI
`tests-build-scripts`). Rojo: 13 de 13 entradas conservaban su fecha. Verde con el `sh` local
y con el `dash` de bookworm.

## 5. Prueba del arreglo

Criterio fijado de antemano: la rama del arreglo, compilada **en la misma copia de trabajo
que falló** (ficheros todavía con fechas del 23-oct y del 4-nov) y con el epoch de `main`,
tiene que dar el SHA de `main`.

| Compilación | SHA-256 |
|---|---|
| `b0bca49` (rama `fix/repro-mtime-includes`) en la copia de trabajo, `SOURCE_DATE_EPOCH=1793814833` | `48c2e1c562f77371a5467cbd8fe959ad2a55b65e2f49881a5ac7331172189992` ✅ |

El build anotó `fechas de config/ fijadas a SOURCE_DATE_EPOCH (114 entradas)`. Mismo SHA que
`main` en CI y que el clon recién hecho: la filtración está cerrada y la ISO no cambia.

## 6. Qué queda

- Otras entradas que llegan a la ISO con fechas del anfitrión y que el recorte no cubre:
  ninguna conocida (el contenido y el resto de metadatos coincidieron entrada por entrada).
- El procedimiento de verificación entre anfitriones (H-001) suma una regla: compilar desde
  la copia de trabajo **y** desde un clon recién hecho; si difieren, hay una filtración del
  disco.
