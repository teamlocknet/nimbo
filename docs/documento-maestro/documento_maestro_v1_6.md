# ⟨NOMBRE POR DEFINIR · codename `nimbo`⟩ — Documento maestro del proyecto
## Ecosistema / sistema operativo de ciberseguridad basado en Debian

**Versión:** 1.6 (Fase 1: 🏁 **BLOQUE 1C (REPRODUCIBILIDAD) CERRADO DE PUNTA A PUNTA.** ISO bit-idéntica, verificable por un tercero en CI, y robusta en el tiempo — las **cuatro capas de la cadena ancladas**. El jefe de nivel #1 quedó completamente resuelto, y temprano.)
**Grupo:** LockNet · **Repo:** `github.com/teamlocknet/nimbo` (público) · **Contexto:** Proyecto de grado — SENA, ADSO
**Fecha:** Septiembre 2026
**Estado:** 🟢 **EN MARCHA, con el jefe de nivel más duro ya vencido.** 2 personas + IA · **13 semanas duras** (sep → dic 2026, sin holgura) · 24/7 · dev en máquinas potentes → target gama baja · alcance **COMPLETO**. Vía A (build+reproducibilidad) de Juan José con su capítulo más difícil terminado; Vía B (Alejandro) aún sin arrancar.

**Cambios frente a v1.5:**
1. **🏁 Bloque 1C cerrado de punta a punta.** Sobre el MATCH local de v1.5 se sumaron:
   - **1C.4 — compuerta de reproducibilidad en CI (PR #10):** workflow `repro-verify.yml` que compila la ISO en **dos runners GitHub-hosted independientes** del mismo commit y **falla si los SHA-256 difieren**. Prueba de "tercero" real vía **`boot_id`** (único por VM), no hostname. Compuerta probada en verde *y* en rojo (rama-scratch descartada). Esto cumple la letra del Acta: *verificado por un tercero*.
   - **1C.5 — anclaje temporal a `snapshot.debian.org` (PR #11):** mirrors de **build** anclados a `NIMBO_SNAPSHOT=20260901T000000Z` (instante inmutable) → reproducibilidad **en el tiempo**, no solo entre runners simultáneos. `Valid-Until` manejado por la vía limpia (`Check-Valid-Until=false` con **GPG intacta**). **Doble estándar documentado:** build anclado / runtime del producto libre (`deb.debian.org`).
   - **1C.6 — toolchain anclada / 4 capas (PR #12):** el propio paquete `live-build` se instala desde el snapshot; `NIMBO_SNAPSHOT` extraído a **`snapshot.env`** como **fuente única** del timestamp (producto + toolchain se mueven juntos con un bump de una línea).
2. **Las 4 capas de la cadena de reproducibilidad quedan ancladas:** (1) imagen base del contenedor por digest (1B) · (2) toolchain `live-build` por snapshot (1C.6) · (3) paquetes del producto por snapshot (1C.5) · (4) receta determinista compresión+orden+caché (ADR-001/002/003).
3. **Matiz honesto registrado (ADR-004):** el `Check-Valid-Until=false` aún **no se ejerció** (el build corrió 5-sep; el Release de seguridad era válido hasta 7-sep) — la defensa está montada y aceptada por apt, actúa en builds posteriores al 7-sep. No es problema, solo saberlo.

**⚠️ Estado ahora mismo (dónde retomar):** **La reproducibilidad está terminada** (bit-idéntica + tercero + temporal + 4 capas). SHA de referencia con todo anclado: `dcfcd41c…a39801`. **Pendiente aguas arriba:** los **merges de Alejandro del stack #8 → #10 → #11 → #12** (en ESE orden) + el PR del maestro v1.6. **Frentes nuevos disponibles:** CLI `nimbo-audit` (corazón del producto, muy IA-acelerable) o Vía B de Alejandro. **Sin cerrar:** Design Partner (D2) y decisión D9 (trixie vs bookworm).

**Nota para Alejandro (merge):** #8, #10, #11, #12 son un **stack apilado**; hay que mergearlos **de abajo hacia arriba y seguidos** (#8→#10→#11→#12), no sueltos, o GitHub descuadra las bases. Luego el PR del maestro v1.6.

---

## 0. ⚠️ DÓNDE QUEDAMOS — LEER PRIMERO PARA RETOMAR

**Fase 1: Pasos 0, 1A, 1B en `main`. 🏁 Bloque 1C (reproducibilidad) COMPLETO en un stack de PRs (#8→#10→#11→#12) que espera merge de Alejandro. Nada nuevo empezado después.**

**Decidido y fijado:**
- Equipo: **Juan José** (@Duque-Londono — build+repro+CLI) + **Alejandro** (@Alejandro-murillo — seguridad/Core OS). Mateo fuera.
- **Deadline: 3 meses duros, sin holgura.** Doc a instructores 1 semana antes → sin renegociar criterios; listón = Acta.
- **Repo:** `teamlocknet/nimbo` público, `main` protegida.
- **Build:** live-build en contenedor Debian bookworm; paridad dev/CI; ISO mínima 260 MB que arranca a login.
- **🏁 Reproducibilidad COMPLETA:** bit-idéntica local (1C.1–1C.3) + verificable por tercero en CI vía boot_id (1C.4) + temporal por snapshot (1C.5) + 4 capas ancladas con `snapshot.env` como fuente única (1C.6). ADRs 001/002/003/004.
- Método: por secciones → nueva versión del maestro. **Briefs = handoffs entre compañeros; prompts = ciclo con Claude Code.** Ritmo iterativo: maratoncita a maratoncita.
- **Codename `nimbo`** (desechable, un slug).

**Lo inmediato:**
1. **Merge del stack por Alejandro:** #8 → #10 → #11 → #12 (en orden) + PR del maestro v1.6.
2. **Elegir el siguiente gran frente** (a decidir con el equipo): **CLI `nimbo-audit`** (corazón, muy IA-acelerable, victoria visible) o **Vía B de Alejandro** (primer `.deb` `nimbo-net` + hardening).
3. **Cerrar Design Partner (D2)** — reloj corriendo.
4. Deuda opcional futura: verificar la reproducibilidad temporal empíricamente re-corriendo la compuerta sobre el mismo commit dentro de semanas (el anclaje inmutable ya la garantiza por construcción).

**Los 3 jefes de nivel (§10):** reproducibilidad bit a bit (**✅ COMPLETA**) · Design Partner (🔴 abierto) · LUKS + TPM 2.0 (pendiente).

---

## 1. Identidad del proyecto

| | |
|---|---|
| **LockNet** | El grupo/colectivo (org GitHub `teamlocknet`). Autor y destinatario de la credibilidad pública. |
| **⟨producto — NOMBRE POR DEFINIR⟩** | El SO que se entrega. **Decisión abierta.** Candidatos heredados: *VELDORA* / *NEXUS Security OS*. |
| **`nimbo`** | **Codename interno desechable** + slug canónico. |

**Convención de nombre:** un **único slug `nimbo`** en TODO → el nombre real entra con **un find-and-replace global**. **Naming heredado a unificar** (VELDORA/NEXUS en docs SENA) al decidir el nombre. Contexto: proyecto de grado SENA (ADSO); criterios de éxito en Acta §13.

## 2. El producto en una frase

*"Un sistema operativo de auditoría basado en Debian Stable que un equipo de ciberseguridad instala y usa el mismo día — navegación endurecida, red privada del propio equipo y trazabilidad de auditorías con evidencia verificable por hash — todo offline, reproducible bit a bit y sin una sola línea de telemetría."*

## 3. Alcance — qué es y qué NO es

**SÍ (todos, v1.0):** Core OS endurecido (ISO live+instalable, Debian+Xfce4, <500 MB idle) · navegación segura (endurecido tipo LibreWolf + puente Tor con detección de fugas) · red aislada (VPN P2P WireGuard/Tailscale bajo demanda) · CLI de auditoría (`init`/`capture`/`report`) · seguridad transversal (reproducibilidad bit a bit, LUKS+TPM 2.0, air-gapped con GPG) · distribución (CI/CD, repo APT propio, releases firmados, ADRs).

**NO:** kernel propio, 32 bits, infra de pago, y — deliberadamente — **cualquier IA dentro del producto.**

**⚠️ Doble plano de la IA:** el **producto** no lleva IA (diseño); el **desarrollo** sí la usa. Construir *con* IA algo que *no contiene* IA no es contradicción — decirlo explícito en la sustentación.

## 4. Arquitectura de software

3 capas (DAS v2.0): **Capa 1** Debian Stable + systemd · **Capa 2** Xfce4 optimizado · **Capa 3** scripts Python 3 (CLI de auditoría + `nimbo-net`). **Patrones del CLI:** Command + Repository. Estructura del monorepo/CLI/engagement: §4.1–4.3 de v1.1, en `main`.

**Build/reproducibilidad (COMPLETO):** live-build corre **dentro** de un contenedor `debian:bookworm-slim` (por digest). Un solo `build-in-container.sh` sirve local (podman rootful) y CI (docker) → **paridad dev/CI**. **Cadena de reproducibilidad a 4 capas, todas ancladas** (ver §5/§9). Timestamp único en `iso/live-build/snapshot.env`. Arnés de medición en `repro/`; compuerta automática en `repro-verify.yml` (dos runners → mismo SHA o falla).

## 5. Los módulos — mapa de trabajo, dueños y palanca de IA

| Módulo | Dueño | Palanca de IA | Riesgo | Estado |
|---|---|---|---|---|
| ISO live-build + Xfce4 endurecido | Juan José | Media | Medio | ISO mínima ✅; falta Xfce4/hardening |
| CI/CD + repo APT + releases firmados | Juan José | Alta | Medio | CI compila + compuerta repro ✅; falta APT/releases |
| **Reproducibilidad bit a bit** | **Juan José** | **Baja** (empírico) | **Muy alto** | **🏁 COMPLETA (bit-idéntica + tercero + temporal + 4 capas)** |
| **CLI de auditoría** | **Juan José** | **Muy alta** | Bajo | Pendiente — candidato a siguiente frente |
| Hardening + navegadores + Tor | Alejandro | Media-alta | Medio | Pendiente |
| VPN P2P + `nimbo-net join` | Alejandro | Alta | Bajo | Pendiente |
| LUKS + TPM 2.0 (swtpm) | Alejandro | Media | Medio-alto | Pendiente |
| Air-gapped (`nimbo-update-offline`) | Alejandro | Media-alta | Bajo | Pendiente |
| QA / benchmarks RAM / smoke tests | Compartido (CI) | Alta | Medio | Validación ISO ✅ base |
| Docs, ADRs, documento maestro | Compartido + orquestador | Muy alta | Bajo | Al día (v1.6); ADR-000..004 |

## 6. Stack

Debian Stable + **live-build** (en contenedor, toolchain anclada) · Xfce4 · **Python 3 / Typer** · **GitHub Actions** + **Pages** · **aptly** · **WireGuard** vía **Tailscale** (o Headscale) · **Calamares** · **LUKS + systemd-cryptenroll + TPM 2.0** (**swtpm**) · **QEMU/KVM** headless · **GPG** · **diffoscope** · **snapshot.debian.org** · **podman/docker** · **Git**. Todo FOSS, infra **$0**.

## 7. Método de trabajo

- **Roles:** **chat ORQUESTA** (piensa, escribe prompts maestros, revisa, mantiene este doc; no escribe código del producto) · **Claude Code programa** · **el equipo ejecuta, decide, verifica con los ojos** y hace lo del mundo físico (permisos, repo, operaciones privilegiadas/sudo, hardware/TPM, Design Partner).
- **Briefs vs prompts:** briefs = handoffs entre los dos compañeros; Claude Code se dirige por prompts (prompt maestro → PLAN → revisión → aprobación por prompt). Claude Code **se detiene en bloqueadores** y **corrige supuestos falsos** antes de codificar (validado repetidamente en 1C — incl. cazar un error del orquestador: hostname vs boot_id en 1C.4).
- **Ritmo iterativo:** maratoncita a maratoncita — un PR por vuelta; se para, se analiza; con pocos tokens se actualiza el maestro antes de cortar.
- **Stacks de PRs:** cuando los PRs se apilan (base de uno = rama del anterior), se mergean **de abajo hacia arriba y seguidos**; no se mandan sueltos a revisión.
- **Contrato anti-choque:** cada componente consume el output del otro **por referencia**. CODEOWNERS + `main` protegida + ramas `iniciales/tema` + PRs pequeños.
- **Reproducibilidad desde el día 1** · **ritual de cierre** (CI verde + verificación con los ojos + commit + push + release firmado en hitos) · **corrección** (test rojo primero — aplicado incluso a compuertas de CI, que se prueban en rojo *y* verde) · **checkpoint en el núcleo** (esquema/pipeline/PCR/hardening/receta → parar y preguntar) · **no modelar sobre resúmenes** (probar, no suponer) · **"compiló" ≠ "es reproducible"; MATCH = hashes iguales, no "sin diffs"** · **no decidir seguridad cansado.**

### Principios no negociables
1. **REPRODUCIBILIDAD VERIFICABLE.** 2. **HERMETISMO.** 3. **COSTO CERO / TODO FOSS AUDITABLE.** 4. **EVIDENCIA CON HASH.** 5. **EL DETERMINISMO PRIMERO.** 6. **VERIFICAR CON LOS OJOS.** 7. **CHECKPOINT EN EL NÚCLEO.**

## 8. Plan de fases (13 semanas — guía; la Vía A fue por la columna del build)

| Sem | Sección / Foco | Entregable "verde" | Estado |
|---|---|---|---|
| 1 | **Columna del build:** 1A ISO mínima · 1B CI compila · 1C reproducibilidad | ISO en `main` + CI + MATCH | 🏁 1A ✅ · 1B ✅ · **1C COMPLETO ✅** |
| 2 | CLI `init` + logging | `init` | ⬜ **← candidato a siguiente** |
| 3 | CLI `capture` (SHA-256) + hardening base Xfce4 (<500 MB) | Evidencia + RAM | ⬜ |
| 4 | CLI `report` (MD→PDF) + Calamares | CLI completo + ISO instalable | ⬜ |
| 5 | Navegador endurecido + Tor + detección de fugas | Navegación | ⬜ |
| 6 | VPN P2P + `nimbo-net join` + docs local | CU-04 y RF-07 | ⬜ (Vía B, en paralelo cuando Alejandro se libere) |
| 7 | Air-gapped (`nimbo-update-offline` + GPG) | RF-CORE-06 | ⬜ |
| 8 | LUKS+TPM en QEMU+swtpm + flujo passphrase | RF-CORE-05 en QEMU | ⬜ |
| 9 | Reproducibilidad bit-idéntica entre 2 runners | RNF-SEC-07 | 🏁 **hecho (adelantado, 1C.4)** |
| 10 | Repo APT (aptly+Pages) + releases firmados | Distribución + release 1 | ⬜ |
| 11 | QA + benchmarks + **auditoría Design Partner** | Hallazgos | ⬜ |
| 12 | ≥70% hallazgos + validación hardware real (TPM) + release final | ISO v1.0 firmada | ⬜ |
| 13 | Docs finales + ensayo de sustentación | Sustentación lista | ⬜ |

**Nota de secuencia:** la columna del build (1A→1B→1C) se hizo primero y adelantó toda la reproducibilidad (incluida la meta de la semana 9). Siguiente gran frente a elegir: CLI o Vía B. Vía B (Alejandro) en paralelo cuando se libere.

## 9. Registro de ejecución

**Fase 0 (CERRADA ✅):** v1.0 → v1.1.

**Fase 1 — Paso 0 Cimientos (✅ PR #1). Paso 1A ISO mínima (✅ PR #2). Paso 1B CI compila (✅ PR #3).**

**Fase 1 — Paso 1C: Reproducibilidad bit a bit (🏁 COMPLETO — stack #8→#10→#11→#12 esperando merge):**
- **1C.1 Diagnóstico (✅ PR #5, mergeado):** arnés `build-twice.sh`+`diff-isos.sh`; diferencia aislada a ~4 bytes; causa xz multihilo.
- **1C.2 Compresión (✅ PR #6, mergeado):** single-thread `-processors 1` (ADR-001). Necesario, no suficiente.
- **1C.3 Orden + caché APT → MATCH local (✅ PR #8, esperando merge):** sortfile completo vía `-sort` nativo (ADR-002) + caché APT desactivado (ADR-003). MATCH `4bcd075e…`, verificación triple.
- **1C.4 Compuerta CI (✅ PR #10, esperando merge):** `repro-verify.yml`, matrix A/B en runners independientes, `verify` falla si difieren. Prueba de tercero vía **boot_id** (corrigió que el hostname de GitHub-hosted colisiona entre VMs — habría sido prueba falsa). Compuerta probada en rojo y verde.
- **1C.5 Anclaje temporal (✅ PR #11, esperando merge):** mirrors de build → `snapshot.debian.org@20260901T000000Z`; `Check-Valid-Until=false` con GPG intacta; doble estándar build/runtime (ADR-004). Compuerta siguió en MATCH `d1bf74a8…`.
- **1C.6 Toolchain anclada / 4 capas (✅ PR #12, esperando merge):** `live-build` instalado desde snapshot; `snapshot.env` como fuente única del timestamp; toolchain=http (pre-ca-certs) con GPG intacta, producto=https. Compuerta en MATCH `dcfcd41c…`. Confirmado que anclar la toolchain no cambió el hash (live-build 1:20230502 era el ya usado).

**Estado de git:** `main` = Paso 0 + 1A + 1B + 1C.1 + 1C.2. **Stack abierto esperando a Alejandro (orden): #8 → #10 → #11 → #12**, luego PR del maestro v1.6. Sin ramas de trabajo nuevas.

## 10. Los 3 jefes de nivel + palanca de IA

**Palanca:** la IA colapsa "código que escribimos"; casi no toca "sistemas que hay que observar". El 24/7 y las máquinas potentes fueron la palanca real de todo 1C.

1. **Reproducibilidad bit a bit (RNF-SEC-07) — 🏁 COMPLETA.** Bit-idéntica + verificable por tercero (CI, boot_id) + temporal (snapshot) + 4 capas ancladas (imagen base, toolchain, producto, receta). Fuente única del timestamp en `snapshot.env`. Resuelta **temprano** en el cronograma → reconfigura el perfil de riesgo a la baja. **Distinción mantenida:** logramos "*nuestro pipeline* es determinista"; "todo Debian aguas arriba" sigue fuera de alcance y no se exige.
2. **Design Partner (D2)** — riesgo logístico puro; **sigue sin cerrar.**
3. **LUKS + TPM 2.0** — swtpm cubre QEMU; PCR se rompe con updates de kernel. Meta: receta validada en QEMU+swtpm; hardware real como extra.

## 11. Recursos y costo cero

Escaso: tiempo y expertise, no dinero. Infra $0. No monetario: build ~6–8 min (holgado) + **una máquina con TPM 2.0 real** para la semana 12. Curva de live-build: domada. `snapshot.debian.org` puede ir lento/rate-limited (mitigado con Retries=5); hasta ahora sin guerra.

## 12. Decisiones abiertas y pendientes

| # | Ítem | Estado |
|---|---|---|
| D1 | **Nombre real del proyecto** | 🔴 Abierto (codename `nimbo` cubre el interín) |
| D2 | **Cerrar Design Partner** (o plan B) | 🔴 **Sigue abierto** |
| D3 | Reconciliar cronograma | ✅ 3 meses duros, sin holgura |
| D4 | Actualizar docs SENA a 2 personas | 🟠 Antes de la entrega final |
| D5 | Renegociar criterio de reproducibilidad | ⚫ Cerrada: no se renegocia |
| D6 | Owner de Python del CLI | ✅ Juan José |
| D7 | Codename provisional | ✅ `nimbo` |
| D8 | Por cuál vía arranca Juan José | ✅ Build (columna 1A→1B→1C, completa) |
| D9 | Qué Debian Stable se envía (trixie vs bookworm) | 🟠 **Abierto** — anclado a bookworm (oldstable) conscientemente en 1C.5/1C.6; decidir aparte |
| D10 | Siguiente gran frente: CLI `nimbo-audit` vs Vía B de Alejandro | 🟠 **A decidir** en la próxima sesión |

## 13. Riesgos y deuda

- **Cronograma:** 13 semanas duras, cero margen. *Mitigante grande:* el jefe de nivel más peligroso (reproducibilidad) resuelto completo y temprano.
- **Técnico:** reproducibilidad 🏁 hecha; TPM/PCR (medio-alto, pendiente); tamaño gama baja (bajo, 260 MB).
- **Logístico:** Design Partner sin cerrar (alto).
- **Deuda menor (no urgente):** warning de deprecación Node 20 en las actions (subir a v5 en una vuelta de limpieza); verificación empírica temporal de la reproducibilidad (re-correr la compuerta en semanas; garantizada por construcción).

---

*v1.6 — El capítulo más difícil quedó escrito, y quedó entero. Empezamos temiendo la reproducibilidad como se teme una cima con niebla, y resultó ser una escalera: cada peldaño era una capa que escondía la siguiente. La compresión que barajaba bloques. El orden en que se recogen los archivos. Un caché de APT que se reescribía solo. Y cuando por fin dos discos nacieron gemelos en una misma máquina, subimos otro peldaño: que fueran gemelos en dos máquinas distintas de la nube —no por confianza, sino por prueba, con un identificador que no se puede falsear—. Y todavía otro: que sigan siendo gemelos dentro de un mes, congelando en el tiempo hasta el último paquete que entra. Y el último, el que casi se nos escapa y no se nos escapó porque lo dijimos en voz alta: anclar también la herramienta que construye, para que ni ella pueda cambiar bajo nuestros pies. Cuatro capas, cuatro anclas, una sola línea que las gobierna a todas. No quedó un cabo suelto ni un centímetro regalado. Lo más duro del proyecto está hecho, y está hecho temprano —lo que significa que de aquí a diciembre el terreno es más laborioso pero menos incierto—. Guardamos esta victoria completa en la bitácora, esperando solo que cuatro manos la sellen en main. Y mañana elegimos el próximo frente con la tranquilidad de quien ya venció a su peor enemigo.*
