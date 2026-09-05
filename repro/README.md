# repro

Arnés de **reproducibilidad bit a bit** de la ISO (Paso 1C). Es uno de los 3 "jefes de
nivel" del proyecto.

**Dueño:** Juan José

> **1C es iterativo, maratoncita a maratoncita, un PR por vuelta:** medir la diferencia →
> cerrar UNA fuente de no-determinismo → volver a medir. Este arnés es el instrumento de
> medida; **no cierra** ningún no-determinismo por sí mismo.

## Qué hace (Paso 1C.1: solo MEDIR)

1. `build-twice.sh` compila la ISO **dos veces** del **mismo commit**, con el **mismo
   `SOURCE_DATE_EPOCH`**, reutilizando el build en contenedor de 1A/1B
   (`iso/live-build/build-in-container.sh`) **sin modificarlo**. Copia cada resultado a
   `repro/out/iso-A/` y `repro/out/iso-B/`, imprime el **SHA-256** de cada una y el veredicto
   **MATCH/DIFFER**.
2. `diff-isos.sh` compara las dos ISOs con **diffoscope** (en contenedor Debian, con
   `genisoimage`/`xorriso`/`squashfs-tools`/`cpio`/`mtools`/`xxd` para descender por cada
   capa) y genera `repro/out/reporte-diffoscope.html` + `.txt`. Además, como `unsquashfs` no
   puede crear device nodes en rootless, hace un **análisis del squashfs sin privilegios**:
   `unsquashfs -s` (superbloque) y `-lls` (listado con permisos/mtimes/orden) de cada ISO, y
   los diffea (`sq-*.superblock.txt`, `sq.listado.diff`) — esto clasifica el no-determinismo
   (timestamps vs orden vs compresión) sin extraer nada.

### Aislar el ruido del mirror (para un diagnóstico nítido)

No congelamos el mirror todavía (`snapshot.debian.org` es una vuelta futura, no este PR).
Para **separar** las diferencias "por versión de paquete" de las "intrínsecas del pipeline",
`build-twice.sh` guarda el manifiesto `live-image-amd64.packages` de cada corrida y los
**diffea** (`repro/out/packages.diff`):

- Manifiestos **idénticos** → cualquier diferencia entre las ISOs es **intrínseca del
  pipeline** (timestamps, orden en squashfs, compresión, timestamp del ISO…).
- Manifiestos **distintos** → esos paquetes son la clase **"versión de paquete"** (se cierra
  anclando a `snapshot.debian.org` en una vuelta futura).

Como los dos builds corren pegados (minutos), en la práctica los manifiestos salen idénticos
casi siempre; el diff lo **comprueba** en vez de suponerlo.

## Cómo correrlo

**Paso 1 — los dos builds (necesita privilegios, como 1A/1B):**
```bash
sudo ./build-twice.sh
```
Pesado: ~15–40 min en total (dos builds). Al terminar imprime SHA-256 A/B y MATCH/DIFFER, y
devuelve la propiedad de `repro/out/` a tu usuario.

**Paso 2 — el reporte (rootless, sin sudo):**
```bash
./diff-isos.sh
```
Genera `repro/out/reporte-diffoscope.html` (ábrelo en el navegador) y `.txt`.

Las salidas (`repro/out/`: ISOs, manifiestos, reportes) están en `.gitignore`; son
artefactos, no se versionan. Aquí solo viven los **scripts** del arnés y este README.

## Fuera de alcance en 1C.1

Solo mide. **No** cierra no-determinismos, **no** toca `snapshot.debian.org`, **no** cambia
compresión/squashfs, **no** entra al workflow de CI (la comparación en CI es una vuelta
futura, igual que el build local de 1A precedió al CI de 1B). No modifica `iso/live-build/`
(lo invoca, no lo reescribe).

## La compuerta en CI (Paso 1C.4)

Este arnés (`build-twice.sh`) es la verificación **local**: dos builds en la misma máquina.
La verificación **por un tercero** —dos builds en **runners independientes** del mismo
commit— vive en CI, en **`.github/workflows/repro-verify.yml`**:

- Un job `prep` fija un único `SOURCE_DATE_EPOCH` (del commit) para ambos builds.
- Una matrix `leg=[A,B]` compila la ISO **dos veces, cada leg en su propia VM limpia** de
  GitHub-hosted (reutilizando `build-in-container.sh`, sin tocar la receta), y publica su
  SHA-256 como artifact de texto (no sube la ISO: la compuerta solo necesita el hash).
- Un job `verify` compara los dos SHA **entre sí** (nada hardcodeado) y **FALLA** si difieren;
  además **afirma en el summary** que A y B corrieron en runners distintos. Así el resumen
  muestra las dos pruebas del Acta de un vistazo: **hashes idénticos** Y **runners distintos**.

Triggers: `workflow_dispatch` + `push`/`pull_request` a `main` con filtro a
`iso/live-build/**`. Es la compuerta que cierra el "verificado por un tercero" de RNF-SEC-07.
