# ADR-016 — Espejo parcial propio del snapshot anclado

**Estado:** Propuesto

## Contexto

[ADR-004](ADR-004-anclaje-temporal-snapshot-debian-org.md) ancla toda la compilación a
`snapshot.debian.org` con un timestamp fijo (`snapshot.env`). Eso hace la ISO reproducible a
lo largo del tiempo, pero ata **cada** compilación a un servicio externo que no controlamos.

- **Inestabilidad medida:** 2 compilaciones caídas el 4-nov y 7 el 5-nov (HTTP 503 y
  descargas cortadas, p. ej. `Err:18 … libpython3.11-minimal`). Cada caída de una pierna deja
  la compuerta MATCH ×2 sin cerrar: la de `main` estuvo abierta del 5 al 8-nov.
- **Volumen:** unos 500 MB por compilación (≈ 50 MB bootstrap, ≈ 240 MB paquetes del chroot,
  ≈ 13 MB binary e índices descargados varias veces). `lb clean --purge` vacía la caché de
  live-build en cada build, así que en CI todo se baja siempre, dos veces por compuerta.
- **La URL no entra en la ISO:** en la ISO de `main` (`48c2e1c5…`) no aparece
  `snapshot.debian.org` en ningún fichero (dentro ni fuera del squashfs; 8-nov), y
  `/var/lib/apt/lists` queda vacío (`--apt-indices false`). Servir los mismos bytes desde otra
  URL no debería cambiar el SHA; se exige demostrarlo.

Alternativas evaluadas (8-nov):

| | Opción | Por qué no |
|---|---|---|
| A | Conservar la caché de live-build entre builds | Los índices se siguen bajando del snapshot; además cambia cómo construye live-build (más riesgo para el SHA) |
| B | `apt-cacher-ng` delante del snapshot | Dependencia nueva, obliga a http para el producto, otro servicio que mantener |
| **C** | **Espejo parcial propio** | Elegida |

## Decisión

Las compilaciones descargan del **espejo parcial propio**: un servidor HTTP mínimo
(`repro/espejo/espejo.py`, solo biblioteca estándar de Python) en `127.0.0.1` que sirve las
rutas del snapshot anclado desde un directorio local y, si una ruta no está, la descarga una
vez de `snapshot.debian.org`, la guarda y la sirve.

1. **Mismos bytes, misma firma.** El espejo guarda los ficheros originales del snapshot
   (`InRelease`/`Release.gpg` firmados por Debian, índices, `.deb`) sin tocarlos. apt y
   debootstrap verifican la firma GPG y el hash de cada fichero igual que hoy: un fichero
   alterado en el espejo hace **fallar** el build, no lo cambia en silencio.
2. **Solo lo inmutable.** Solo sirve rutas bajo `/archive/{debian,debian-security}/<NIMBO_SNAPSHOT>/`,
   que snapshot.debian.org garantiza inmutables. Cualquier otra ruta → 404. Por eso se puede
   guardar para siempre sin caducidad.
3. **Se llena solo.** No hay lista de paquetes que mantener: el espejo guarda exactamente lo que
   pide la compilación (incluidas las rutas `by-hash` y las variantes que apt prueba). Las
   descargas se escriben en un temporal y se renombran al terminar (nunca queda un fichero a
   medias); un fallo del snapshot da 502 y no se guarda.
4. **Modo `--solo-cache`.** Sin acceso a la red: lo que no esté → 404. Sirve para demostrar que
   una compilación salió entera del espejo.
5. **Activación explícita.** `NIMBO_ESPEJO=http://127.0.0.1:<puerto>` hace que `auto/config`
   (producto) y `build-in-container.sh` (toolchain) usen el espejo. **Sin la variable, todo
   sigue igual que hoy** (snapshot directo).
6. **CI.** `build-iso` y las **dos piernas** de `repro-verify` usan el espejo. El directorio se
   restaura y se guarda con `actions/cache` (clave por timestamp del snapshot; como todo es
   inmutable, sirve cualquier caché anterior del mismo timestamp). Solo se guarda una caché
   nueva si hubo descargas.
7. **Run semanal contra el snapshot.** Un `repro-verify` programado (semanal, sobre `main`)
   compila la pierna A con el espejo y la B directo del snapshot, y exige MATCH: prueba de
   forma continua que el espejo y el snapshot dan la misma ISO.

## Consecuencias

- **Más fácil:** las compuertas dejan de caer por el snapshot cuando la caché está caliente;
  builds más rápidos; la misma herramienta sirve en local (`~/.cache/nimbo-espejo`).
- **No elimina del todo la dependencia:** con la caché fría (primer build de un timestamp
  nuevo, o tras 7 días sin uso, que es cuando GitHub la expulsa) se descarga del snapshot.
  Una ruta caída sigue dando 502 y el build falla en rojo (PR #36). La siguiente compilación
  reutiliza todo lo ya guardado.
- **Coste:** ≈ 350–500 MB de caché en Actions (límite del repo: 10 GB). $0.
- **Confianza:** el espejo no añade confianza nueva: la cadena sigue siendo la firma de Debian
  verificada por apt/debootstrap (ADR-004). El espejo es código nuestro (~150 líneas, sin
  dependencias) con tests.
- **Riesgo para el SHA:** si la URL del mirror llegara a la ISO por algún camino no medido, el
  SHA cambiaría. Criterio de aceptación: con el espejo, el commit de `main` compilado con su
  epoch da **exactamente** `48c2e1c5…`; y el run semanal lo vigila.
- **Fuera de alcance:** publicar el espejo como fuente pública o como release (si la caché de
  Actions resulta insuficiente, se evalúa en otro ADR).

## Prueba de integración (8-nov)

Criterio: `main` (`3825b0e`, epoch `1793814833`) compilado en el PC de Juan José con el
espejo tiene que dar `48c2e1c5…` (la ISO de CI de `main`, MATCH ×2). Hicieron falta dos
correcciones, las dos encontradas comparando las ISO fichero a fichero:

| Intento | SHA-256 | Qué faltaba | Causa |
|---|---|---|---|
| 1 | `baf4f94e…` | 22 paquetes (firmware y dependencias) | live-build pide `…/<snapshot>//dists/…`; el espejo rechazaba la doble barra y se perdió `Contents-amd64.gz`, con el que live-build elige el firmware (`--firmware-chroot`). Arreglo: normalizar barras como hace el snapshot (test rojo → verde) |
| 2 | `d89b59d8…` | `ca-certificates`, `openssl` | debootstrap 1.0.128 añade `ca-certificates` al base **solo si el mirror es https** (`scripts/debian-common`). La ISO dependía del esquema del mirror. Arreglo: `--debootstrap-options "--include=ca-certificates"` en `auto/config` |
| 3 | **`48c2e1c5…`** ✅ | — | espejo (http) + include |
| control | **`48c2e1c5…`** ✅ | — | snapshot directo (https) + include: **la ISO de CI no cambia** |

Además: con `--solo-cache` (sin acceso al snapshot) el espejo sirvió los 705 ficheros que
pidió la compilación (sin una descarga) y dio el mismo SHA que en modo normal. Tamaño del
espejo para este timestamp: ≈ 385 MB.

Las dos causas son del mismo tipo que [H-004](../hallazgos/H-004-mtime-includes-chroot.md):
una propiedad del **entorno de build** (la ruta pedida, el esquema del mirror) se colaba en
la ISO sin que nadie lo hubiera decidido. El espejo las destapó; el run semanal (pierna B
directa del snapshot) vigila que no aparezca otra.

**Observación para 3B.2 (no se toca aquí):** `--firmware-chroot` (activo por defecto)
instala el firmware que live-build deduce del `Contents`, p. ej. `indi-dsi` (driver de una
cámara de astronomía) con `libcurl3-gnutls` y `libssh2`. Es superficie que nadie eligió;
desactivarlo cambia la ISO y puede afectar al hardware real.

## Fecha

2026-11-08
