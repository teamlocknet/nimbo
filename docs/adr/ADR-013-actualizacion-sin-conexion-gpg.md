# ADR-013 — Actualización sin conexión con paquetes firmados (`nimbo-update-offline`)

**Estado:** Aceptado (16-nov, Juan José al aprobar este cambio; revisado en #49, medido en #89) ·
**Autor:** Emmanuel ·
**Aceptación de RF-UPD-01:** Juan José, dentro de RNF-03 (decisión del 10-nov)

## Contexto

- **RF-UPD-01 (Alta) / HU-14:** "actualizarse sin conexión con `nimbo-update-offline`,
  aceptando solo paquetes firmados con GPG". CA-1: un paquete con firma válida se instala
  sin red. CA-2: uno con firma inválida o sin firma se rechaza. CA-3: *se rechaza el 100 %
  de los paquetes con firma inválida* del conjunto de pruebas.
- El cotejo (G1) señaló que E7 ("air-gapped con GPG") no tenía entregable con ese nombre ni
  ese criterio, y propuso reescribirla así; este ADR la aplica.
- Restricciones: sin red (RNF-03), solo bookworm `main`, **ninguna clave en el repositorio**;
  las claves reales las custodia Juan José. 3B.1 ya deshabilitó las actualizaciones
  automáticas: el camino de actualización del producto es este.

## Opciones

| Opción | A favor | En contra |
|---|---|---|
| A. Repositorio APT firmado en la USB (`Release.gpg` + `apt` con `file:`) | Usa la verificación de `apt` | Exige generar un repositorio completo por lote; mezcla con ADR-015 (repo APT de Alejandro); el rechazo de "extras" queda en manos de la configuración de `apt` |
| **B. Lote = `.deb` + `MANIFIESTO` firmado (firma separada) verificado con `gpgv`** | Simple de preparar y auditar; cada regla de rechazo es explícita y probada; `gpgv` ya viene con `apt` | Un formato propio (pequeño), documentado aquí |
| C. Firmar cada `.deb` (`debsigs`/`dpkg-sig`) | Firma por paquete | `debsig-verify` exige políticas por clave; más piezas; `dpkg-sig` ya no está en bookworm |

## Decisión (aceptada el 16-nov): B

- `nimbo-update-offline preparar <lote> --clave <id>` (equipo de firma): escribe
  `MANIFIESTO` (`<sha256>  <nombre.deb>`) y su firma separada `MANIFIESTO.asc`.
- `nimbo-update-offline verificar <lote>`: acepta **solo** si la firma es válida para
  `/usr/share/nimbo/keyrings/nimbo-actualizaciones.gpg` (`gpgv`, `VALIDSIG`), el manifiesto
  no está vacío ni repite nombres, cada nombre es un `.deb` **sin rutas**, el directorio
  tiene exactamente esos `.deb` y cada SHA-256 coincide. Ante cualquier duda, rechaza.
- `sudo nimbo-update-offline instalar <lote>`: copia el lote a un directorio propio,
  **verifica la copia** (evita cambiar la USB entre verificar e instalar) e instala con
  `apt-get install -y` **sin ninguna fuente remota** (`Dir::Etc::sourcelist` y `sourceparts`
  vacíos), así que no puede descargar nada. Si se rechaza, no instala nada. *(La versión
  anterior usaba `--no-download`, pero con `.deb` locales el apt de bookworm falla con
  "Internal Error, Pathname to install is not absolute": la instalación real no funcionaba.
  Medido en VM el 11-nov; las pruebas unitarias no lo veían porque simulan `apt-get`.)* **Usa siempre el anillo de
  nimbo y no admite `--anillo`** (revisión de #49): si lo admitiera, un lote firmado por
  cualquiera podría traer su clave y pedir que se usara. `--anillo` queda solo en `verificar`,
  que no instala.
- Cualquier dato raro (MANIFIESTO que no es UTF-8, un directorio con nombre `.deb`, un fichero
  ilegible) se **rechaza con su motivo**, nunca con un *traceback*.
- **Claves (decisión de Juan José, 16-nov):** los lotes los firma **la clave de release**
  (ADR-015, huella primaria `0C50 B739 1A9B 8CFF 8A36  A627 D3B9 111F EC57 48C6`): una sola
  raíz de confianza para la ISO y para sus actualizaciones, con la huella ya publicada en el
  `README.md`, y ninguna clave más que custodiar. Juan José firma cada lote con la subclave
  de firma (la frase la teclea él; nunca pasa por el chat ni por el repo). El paquete lleva
  solo la **parte pública**, en `debian/keyrings/nimbo-actualizaciones.gpg` (binaria, de
  `release/nimbo-release-publica.asc` con `gpg --dearmor`), que instala en
  `/usr/share/nimbo/keyrings/`. El desarrollo y las pruebas usan claves efímeras.
- **Firma aceptada:** `gpgv` con código 0, **una sola `GOODSIG` y una sola `VALIDSIG`**, y
  ningún estado de revocación, caducidad o error (`REVKEYSIG`, `EXPKEYSIG`, `EXPSIG`,
  `BADSIG`, `ERRSIG`, `NO_PUBKEY`, `KEYEXPIRED`, `SIGEXPIRED`, `KEYREVOKED`). `gpgv` da 0 y
  `VALIDSIG` también con una clave revocada o caducada (medido el 16-nov); mismo criterio que
  `release/release.py` (#74).

## Cómo se verifica

| Criterio | Prueba | Resultado |
|---|---|---|
| CA-1 (lógica) | Lote válido firmado con la clave de prueba → `ACEPTADO`; `instalar` llama a `apt-get` sin fuentes remotas con las copias | ✅ (pytest) |
| Instalación real con `apt` | VM Debian 12: las opciones de `instalar` con un `.deb` local | ✅ 11-nov: instala (código 0). Con `--no-download`, `Internal Error` |
| CA-2 / CA-3 | **N = 10** lotes manipulados (sin firma, sin manifiesto, manifiesto alterado, otra clave, firma basura, byte cambiado, `.deb` extra, `.deb` ausente, ruta firmada, manifiesto vacío firmado) | ✅ 10/10 rechazados, cada uno con su motivo (100 %); + **caso 11** (lote de otra clave con su propio anillo y `--anillo`: `instalar` no admite la opción y lo rechaza) y los 2 casos de datos raros |
| Rojo → verde | Pruebas escritas antes que el código | Rojo: 2 errores de colección → verde: 16 passed. Revisión de #49: 6 failed → 20 passed |
| Prueba sin red, ISO `30b5958f…` (16-nov) | VM **sin tarjeta de red**, instalada con Calamares: 1 lote de control + **13 inválidos** (los 10 de antes + firma de otro fichero, **clave revocada**, **clave caducada**) — `repro/evidencia/2026-11-16-rnf03-sin-red.md` | 12/14 en la VM: **revocada y caducada aceptadas** (arreglado, rojo → verde); **la ISO no traía el anillo** (añadido al paquete; `verificar-cli-rootfs.sh` lo exige) |
| CA-1 real, sin red (RNF-03) | ISO de #89 (`7d0da21c…`, MATCH ×2) con el anillo, VM sin tarjeta de red: un lote **firmado por Juan José** con la clave de release y los mismos inválidos | ✅ 16-nov: el lote firmado **se instala sin red** (`dpkg`: instalado); **14/14 rechazados (100 %)**; `rnf03-en-vm.sh` 0 fallos de 37 |

## Consecuencias

- **Gana:** RF-UPD-01 con un criterio medible (100 % de rechazos en un conjunto explícito) y
  un procedimiento por USB documentado en `packages/nimbo-update-offline/README.md`.
- **Paga:** un formato de lote propio. Las dependencias de un `.deb` nuevo deben venir en el
  mismo lote o estar ya instaladas (sin fuentes remotas, `apt` no busca nada fuera).
- **Depende de:** la clave de release (ADR-015, Juan José) y la integración a la ISO (ADR-020).
- **Paga (clave compartida):** si la clave de release se revoca, también deja de valer para
  las actualizaciones; las dos cosas se reemiten juntas.
- **Límite de v1 — repetición y bajada de versión:** un lote viejo pero bien firmado sigue
  siendo válido para siempre. `apt-get -y` sin `--allow-downgrades` **se niega a bajar de
  versión: medido en VM el 11-nov** (`pruebas/prueba-bajada-version.sh`: la 1.0 se rechaza con
  código 100 y la 2.0 sigue instalada). Si da el tiempo: fecha o número de serie dentro del
  MANIFIESTO firmado.
- La "evidencia firmada" del E7 original no respalda ningún requisito (cotejo G1): queda fuera.

## Fecha

2026-11-09 · revisado 2026-11-10 (#49) · 2026-11-16 (clave de release, criterio de firma, prueba sin red) · aceptado 2026-11-16
