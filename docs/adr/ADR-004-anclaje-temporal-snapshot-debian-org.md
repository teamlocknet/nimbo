# ADR-004 — Anclaje temporal a snapshot.debian.org

**Estado:** Aceptado

## Contexto

Tras cerrar el MATCH bit-idéntico local ([ADR-001](ADR-001-compresion-determinista-squashfs.md)
compresión · [ADR-002](ADR-002-orden-determinista-empaquetado-squashfs.md) orden ·
[ADR-003](ADR-003-cache-apt-determinista-squashfs.md) caché APT) y llevar la verificación a CI
con dos runners independientes (Paso 1C.4, compuerta `repro-verify.yml`), quedaba una fuente de
no-determinismo **abierta y temporal**: los mirrors por defecto (`deb.debian.org`) son
*rolling*. Hoy el MATCH funciona porque los dos builds corren **simultáneos** y bajan las
mismas versiones de paquete; pero **el mismo commit compilado dentro de un mes podría jalar
paquetes más nuevos → hash distinto**. Eso no cumple el criterio del Acta ("mismo commit →
mismo hash") **a lo largo del tiempo**, solo entre runners simultáneos.

`snapshot.debian.org` archiva el estado del repositorio Debian indexado por timestamp y es
**inmutable**: para un timestamp dado sirve exactamente los mismos índices y `.deb` sin
importar cuándo se descarguen. Anclar los mirrors de *build* a un timestamp fijo convierte las
versiones de paquete en una entrada **fija y versionada en el repo**, cerrando la
reproducibilidad **temporal** por construcción.

**Borde conocido — `Valid-Until`:** el `Release` de `main` de bookworm **no** trae
`Valid-Until` (solo `Date`), pero el de `bookworm-security` **sí**, y corto (~7 días). Con un
snapshot cuyo `Valid-Until` ya pasó, `apt` considera los metadatos caducados y **aborta**.

## Decisión

Anclar el **build** a `snapshot.debian.org` con un timestamp fijo, definido en **una sola
fuente de verdad**, `iso/live-build/snapshot.env`:

```
NIMBO_SNAPSHOT="20260901T000000Z"
```

Ese archivo lo **sourcean los dos scripts** que necesitan el anclaje —`build-in-container.sh`
(toolchain) y `auto/config` (producto)— de modo que el timestamp vive en **un único sitio** y
un bump futuro es una sola línea, sin acoplar ambos scripts entre sí.

- **Paquetes del PRODUCTO (mirrors de build en `auto/config`):** `--(parent-)mirror-bootstrap`,
  `--(parent-)mirror-chroot` y `--(parent-)mirror-chroot-security` →
  `.../archive/debian/${NIMBO_SNAPSHOT}/` y `.../archive/debian-security/${NIMBO_SNAPSHOT}/`
  (https; para entonces `ca-certificates` ya está instalado). Determinan las versiones de
  paquete del sistema y, por tanto, los bytes de la ISO.
- **TOOLCHAIN (`live-build`, en `build-in-container.sh`):** antes de `apt-get install
  live-build ca-certificates`, se re-apunta el apt del contenedor al mismo snapshot
  (`http://snapshot.debian.org/archive/debian/${NIMBO_SNAPSHOT}/ bookworm main`). Así el propio
  generador de la ISO queda fijo, no *rolling*.
  - **Por qué toolchain=http y producto=https (no es incoherencia):** la imagen base
    `bookworm-slim` **no trae `ca-certificates`** — se instala precisamente en ese `apt-get`.
    El primer apt, por tanto, no puede hablar TLS todavía, así que usa **http**. La seguridad
    no depende del transporte sino de la **firma GPG del `Release`**, que apt verifica en
    ambos casos (no se toca `apt-secure`). Una vez instalado `ca-certificates`, los mirrors del
    producto (debootstrap/chroot) ya usan **https**. El transporte no altera los bytes.
- **Doble estándar deliberado (build anclado / runtime libre):** los mirrors `binary` —el
  `sources.list` que queda **dentro** de la ISO— **NO** se anclan; se dejan en los defaults de
  live-build (`deb.debian.org` / `security.debian.org`). El **build** se fija a snapshot por
  *reproducibilidad*; el **runtime** del producto apunta a los mirrors normales por
  *usabilidad* (y nimbo tiene su propia vía de update offline). No es una inconsistencia: el
  contenido de ese `sources.list` es un string fijo, así que sigue siendo determinista; solo
  desacopla "con qué se construyó" de "contra qué actualiza el sistema instalado".
- **Valid-Until (vía limpia, no hack):** `--apt-options "--yes -o
  Acquire::Check-Valid-Until=false -o Acquire::Retries=5"`, **manteniendo
  `LB_APT_SECURE=true`**. Se sigue verificando la **firma GPG** del `Release`; solo se relaja
  el chequeo de **vencimiento por fecha**, que para un snapshot inmutable no aporta seguridad.
  Es la práctica que Debian y reproducible-builds recomiendan para builds desde snapshot.
  `Retries=5` amortigua la intermitencia/rate-limit de snapshot.d.o.

Se ancla a **bookworm** de forma consciente: es la base sobre la que se construyó todo 1A–1C.
En la fecha de este ADR bookworm es **oldstable** (trixie/Debian 13 ya es stable); se ancla a
oldstable **a propósito** para no mezclar "reproducibilidad" con "cambio de versión de Debian".

**Las CUATRO capas del build quedan ancladas** (cadena de reproducibilidad completa):

1. **Imagen base del contenedor** → por *digest* (Paso 1B): fija el entorno de arranque.
2. **Toolchain** (`live-build` y deps) → por *snapshot* (Paso 1C.6): fija el generador de la ISO.
3. **Paquetes del producto** (debootstrap + chroot + security) → por *snapshot* (Paso 1C.5):
   fija el contenido del sistema.
4. **Receta determinista** → compresión/orden/caché APT (ADR-001/002/003): fija cómo se
   empaqueta ese contenido.

Las capas 2 y 3 comparten el **mismo** `NIMBO_SNAPSHOT` (de `snapshot.env`) → toolchain y
producto se mueven siempre juntos. Todas son de la era bookworm → coherentes.

## Consecuencias

- **Reproducibilidad temporal por construcción:** fijadas las versiones de paquete (única
  entrada que variaba) y siendo el pipeline ya bit-idéntico dada una entrada fija (1C.1–1C.4),
  dos builds del mismo commit **separados en el tiempo** producen el mismo SHA-256. La
  compuerta de CI (simultánea) sigue siendo la corroboración; el anclaje inmutable es la
  garantía temporal.
- **Se congela la seguridad hasta re-anclar:** el sistema construido trae los paquetes (y
  parches de seguridad) **hasta `NIMBO_SNAPSHOT`**, no más nuevos. Actualizar seguridad =
  **bump consciente** del timestamp (ver abajo). Es el compromiso aceptado: determinismo a
  cambio de depender de snapshot.d.o y de re-anclar deliberadamente.
- **Dependencia de snapshot.d.o:** es más lento y con rate-limit que `deb.debian.org`;
  `Retries=5` lo amortigua. Si comprometiera la fiabilidad del build, se re-evalúa (no se mete
  un workaround sucio).
- **Reversible:** volver a `deb.debian.org` en los mirrors de build restaura el comportamiento
  rolling (a costa de la reproducibilidad temporal).

## Cómo se actualiza el anclaje a futuro (bump consciente)

1. Elegir un timestamp nuevo de snapshot.d.o (p. ej. tras un point-release o un lote de
   parches de seguridad relevantes).
2. Editar `NIMBO_SNAPSHOT` en `iso/live-build/snapshot.env` (**una sola línea, un solo sitio**;
   toolchain y producto se re-anclan juntos) y actualizar este ADR (nuevo timestamp + motivo).
3. Correr la compuerta `repro-verify.yml`: debe seguir en **MATCH** con el nuevo anclaje.
4. Es un cambio **consciente y trazable** (commit + ADR), nunca automático.

## Residuales

- **Toolchain no anclada → RESUELTO en 1C.6.** Antes `build-in-container.sh` instalaba
  `live-build` desde `deb.debian.org bookworm` (*rolling*). Ahora ese `apt-get` sale del mismo
  snapshot (`live-build 1:20230502`, congelado). La cadena queda completa a 4 capas (ver
  arriba); ya no hay superficie *rolling* en el build.
- **`Valid-Until` aún no ejercido (nota, no acción):** en las corridas de verificación
  (2026-09-05) el `Release` de seguridad del snapshot seguía dentro de su ventana
  (`Valid-Until: 2026-09-07`), así que `Check-Valid-Until=false` estaba puesto y aceptado por
  apt pero no llegó a **dispararse**; lo hará en builds posteriores al 7-sep-2026, que es justo
  cuando hace falta. La defensa está montada; nada que hacer.

## Decisión abierta relacionada (NO se resuelve aquí)

- **D9 — Qué Debian Stable se envía finalmente (trixie/Debian 13 vs bookworm).** Este ADR
  ancla a bookworm por continuidad de 1A–1C; **saltar de versión de Debian es otra decisión**,
  a tomar aparte (se registrará en su propio ADR y en el documento maestro). Aquí solo queda
  **anotado como pendiente**.

## Fecha

2026-09-05
