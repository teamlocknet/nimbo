# Créditos y procedencia de los recursos gráficos

Todo el código propio del repositorio está bajo **GPL-3.0-or-later** ([`LICENSE`](LICENSE)).
Este archivo registra **quién hizo y cuándo** cada recurso no textual que viaja en la ISO,
para que su procedencia sea comprobable antes de una release firmada.

## Branding del instalador (Calamares)

| Recurso en la ISO | Fuente en el repo | Autoría | Fecha | Licencia |
|---|---|---|---|---|
| `etc/calamares/branding/nimbo/nimbo.png` (256×256) | [`iso/branding/nimbo.svg`](iso/branding/nimbo.svg) | Equipo LockNet: SVG escrito en el repo por Claude Code bajo la dirección de Juan José Duque | 2026-10-23 | GPL-3.0-or-later |
| `etc/calamares/branding/nimbo/nimbo-bienvenida.png` (800×440) | [`iso/branding/nimbo-bienvenida.svg`](iso/branding/nimbo-bienvenida.svg) | Ídem | 2026-10-23 | GPL-3.0-or-later |

- **Solo geometría** (un anillo `#3daee9` sobre fondo `#14202e`): **sin texto ni tipografías**,
  así que no hay ninguna fuente tipográfica de terceros implicada. El nombre del producto lo
  pinta Calamares a partir de `productName` (`branding.desc`).
- Los PNG se **generan** desde los SVG con [`iso/branding/generar-branding.sh`](iso/branding/generar-branding.sh)
  (`rsvg-convert` de bookworm, en el contenedor anclado del proyecto), de forma determinista.
  Para cambiar el branding se edita el SVG y se regeneran los PNG; nunca se sustituyen a mano.
- **Por qué existe este registro:** los PNG anteriores (Paso 3C.1, commit `2eb22cd`) no tenían
  fuente, metadatos ni registro de procedencia, y llevaban texto con una tipografía sin
  identificar. Se sustituyeron el 2026-10-23 por estos, con fuente versionada.
