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

Anclar el **build** a `snapshot.debian.org` con un timestamp fijo, versionado en
`iso/live-build/auto/config`:

```
NIMBO_SNAPSHOT="20260901T000000Z"
```

- **Mirrors anclados (build):** `--(parent-)mirror-bootstrap`, `--(parent-)mirror-chroot` y
  `--(parent-)mirror-chroot-security` → `.../archive/debian/${NIMBO_SNAPSHOT}/` y
  `.../archive/debian-security/${NIMBO_SNAPSHOT}/`. Son los que determinan las versiones de
  paquete y, por tanto, los bytes de la ISO.
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

**Coherencia con el digest de la imagen base (1B):** la imagen del contenedor
(`debian:bookworm-slim` anclada por digest) aporta solo la *toolchain* (live-build/debootstrap);
los *paquetes del producto* salen del snapshot anclado. Ambos anclajes son de la era bookworm →
coherentes: uno fija las herramientas, el otro fija el contenido.

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
2. Editar `NIMBO_SNAPSHOT` en `iso/live-build/auto/config` (una línea) y actualizar este ADR
   (nuevo timestamp + motivo).
3. Correr la compuerta `repro-verify.yml`: debe seguir en **MATCH** con el nuevo anclaje.
4. Es un cambio **consciente y trazable** (commit + ADR), nunca automático.

## Decisión abierta relacionada (NO se resuelve aquí)

- **D9 — Qué Debian Stable se envía finalmente (trixie/Debian 13 vs bookworm).** Este ADR
  ancla a bookworm por continuidad de 1A–1C; **saltar de versión de Debian es otra decisión**,
  a tomar aparte (se registrará en su propio ADR y en el documento maestro). Aquí solo queda
  **anotado como pendiente**.

## Fecha

2026-09-05
