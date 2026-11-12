# ADR-013 — Actualización sin conexión con paquetes firmados (`nimbo-update-offline`)

**Estado:** Propuesto (9-nov, Emmanuel; revisado en #49) · **Autor:** Emmanuel ·
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

## Decisión (propuesta): B

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
- **Claves:** la de actualizaciones la genera y custodia Juan José (ADR-015). El paquete
  lleva solo su **parte pública**. El desarrollo y las pruebas usan claves efímeras.

## Cómo se verifica

| Criterio | Prueba | Resultado |
|---|---|---|
| CA-1 (lógica) | Lote válido firmado con la clave de prueba → `ACEPTADO`; `instalar` llama a `apt-get` sin fuentes remotas con las copias | ✅ (pytest) |
| Instalación real con `apt` | VM Debian 12: las opciones de `instalar` con un `.deb` local | ✅ 11-nov: instala (código 0). Con `--no-download`, `Internal Error` |
| CA-2 / CA-3 | **N = 10** lotes manipulados (sin firma, sin manifiesto, manifiesto alterado, otra clave, firma basura, byte cambiado, `.deb` extra, `.deb` ausente, ruta firmada, manifiesto vacío firmado) | ✅ 10/10 rechazados, cada uno con su motivo (100 %); + **caso 11** (lote de otra clave con su propio anillo y `--anillo`: `instalar` no admite la opción y lo rechaza) y los 2 casos de datos raros |
| Rojo → verde | Pruebas escritas antes que el código | Rojo: 2 errores de colección → verde: 16 passed. Revisión de #49: 6 failed → 20 passed |
| CA-1 real, sin red (RNF-03) | VM bookworm **sin red**: instalar un lote válido por USB y comprobar un rechazo | *Pendiente* |

## Consecuencias

- **Gana:** RF-UPD-01 con un criterio medible (100 % de rechazos en un conjunto explícito) y
  un procedimiento por USB documentado en `packages/nimbo-update-offline/README.md`.
- **Paga:** un formato de lote propio. Las dependencias de un `.deb` nuevo deben venir en el
  mismo lote o estar ya instaladas (sin fuentes remotas, `apt` no busca nada fuera).
- **Depende de:** la clave real (ADR-015, Juan José) y la integración a la ISO (checkpoint).
- **Límite de v1 — repetición y bajada de versión:** un lote viejo pero bien firmado sigue
  siendo válido para siempre. `apt-get -y` sin `--allow-downgrades` **se niega a bajar de
  versión: medido en VM el 11-nov** (`pruebas/prueba-bajada-version.sh`: la 1.0 se rechaza con
  código 100 y la 2.0 sigue instalada). Si da el tiempo: fecha o número de serie dentro del
  MANIFIESTO firmado.
- La "evidencia firmada" del E7 original no respalda ningún requisito (cotejo G1): queda fuera.

## Fecha

2026-11-09 · revisado 2026-11-10 (#49)
