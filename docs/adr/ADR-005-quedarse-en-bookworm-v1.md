# ADR-005 — Quedarse en bookworm para la v1.0

**Estado:** Aceptado

## Contexto

El proyecto nació con la narrativa "basado en Debian **Stable**" y el build se ancló a
**bookworm (Debian 12)** desde el Paso 1A, cuando bookworm *era* Stable. Eso dejó de ser
cierto: **trixie (Debian 13) es Debian Stable desde el 2025-08-09** y bookworm pasó a
**oldstable**. La decisión quedó anotada como pendiente (D9) en
[ADR-004](ADR-004-anclaje-temporal-snapshot-debian-org.md) y en el documento maestro: ¿qué
Debian se envía finalmente?

Lo que hoy está **validado sobre bookworm**, y solo sobre bookworm:

- **Anclaje temporal:** `snapshot.debian.org` con `NIMBO_SNAPSHOT` fijo
  ([ADR-004](ADR-004-anclaje-temporal-snapshot-debian-org.md)).
- **Contenedor de build** `debian:bookworm-slim` anclado **por digest**, con la toolchain
  (`live-build`) saliendo del mismo snapshot.
- **Reproducibilidad bit-idéntica:** compuerta `repro-verify.yml` en **MATCH**
  ([ADR-001](ADR-001-compresion-determinista-squashfs.md) ·
  [ADR-002](ADR-002-orden-determinista-empaquetado-squashfs.md) ·
  [ADR-003](ADR-003-cache-apt-determinista-squashfs.md)).
- **RAM idle del escritorio Xfce4:** **378 MiB** (<500 MB).
- **Hermetismo** (RNF-01): 0 salientes no solicitadas, 0 listeners, con pcap.

Hay que decidir **ahora**: todo paso nuevo de la ISO (Calamares, LUKS+TPM, hardening fino)
se ancla a la release elegida, así que el costo de migrar solo crece. Y el calendario no
tiene colchón.

**Alternativa descartada — migrar a trixie.** Costo estimado **~1 semana**: re-anclar el
snapshot y el digest del contenedor, y **re-verificar** todo lo anterior (repro MATCH, RAM,
hermetismo) sobre una base de paquetes distinta. Devolvería la etiqueta "Stable" a la
narrativa, pero gastaría una semana que el calendario no tiene en re-ganar garantías que ya
están ganadas, sin aportar ninguna función que la v1.0 necesite.

## Decisión

**Quedarse en bookworm (Debian 12) para la v1.0.** No se migra a trixie. El build, el
anclaje y todas las verificaciones siguen sobre bookworm; D9 queda **resuelta**.

## Consecuencias

- **No se pierde nada de lo validado:** snapshot, contenedor por digest, repro MATCH,
  378 MiB y hermetismo siguen vigentes tal cual. La semana que costaría migrar se invierte
  en lo que falta (Calamares, LUKS+TPM).
- **Target de Python = 3.11** (el de bookworm). El CLI no usa features > 3.11 y debe
  probarse en 3.11 en CI, no solo en el intérprete local.
- **systemd 252.** Suficiente para `systemd-cryptenroll` + TPM2; **no** se dispone de las
  funciones nuevas de systemd 257 (trixie). El diseño de LUKS+TPM se hace contra 252.
- **Calamares = la versión que trae bookworm.** La receta del instalador se escribe contra
  esa versión, no contra la de trixie.
- **Cambia la narrativa.** "Basado en Debian Stable" deja de ser exacto y pasa a
  **"basado en Debian, rama con soporte LTS (bookworm)"**. Es un reencuadre honesto: se
  elige oldstable por reproducibilidad y estabilidad ya verificadas, y se dice explícito en
  la sustentación.
- **Ventana de soporte:** bookworm está en fase **LTS desde el 2026-06-11 hasta el
  2028-06-30** (fuente: <https://wiki.debian.org/LTS>, consultada el 2026-10-06). Cubre con
  holgura la v1.0; los parches de seguridad siguen entrando por *bump consciente* del
  snapshot (ADR-004).
- **Compromiso aceptado:** la base de paquetes es más vieja que la de Stable. Migrar a
  trixie queda como trabajo **posterior a la v1.0**, a registrar en su propio ADR (que
  reemplazaría a este).

## Fecha

2026-10-06
