# ⟨NOMBRE POR DEFINIR · codename `nimbo`⟩ — Documento maestro del proyecto
## Ecosistema / sistema operativo de ciberseguridad basado en Debian

**Versión:** 1.5 (Fase 1: 🏆 **HITO — REPRODUCIBILIDAD BIT-IDÉNTICA LOCAL LOGRADA.** Dos builds del mismo commit producen un `.iso` con **SHA-256 idéntico**. Cayó el jefe de nivel #1. Queda llevar la verificación al CI y anclar versiones para robustez temporal.)
**Grupo:** LockNet · **Repo:** `github.com/teamlocknet/nimbo` (público) · **Contexto:** Proyecto de grado — SENA, ADSO
**Fecha:** Septiembre 2026
**Estado:** 🟢 **EN MARCHA, con un hito grande cerrado.** 2 personas + IA · **13 semanas duras** (sep → dic 2026, sin holgura) · 24/7 · dev en máquinas potentes → target gama baja · alcance **COMPLETO**. Vía A (build+reproducibilidad) de Juan José con su pieza más difícil resuelta; Vía B (Alejandro) aún sin arrancar.

**Cambios frente a v1.4:**
1. **🏆 Paso 1C.3 CERRADO — MATCH bit-idéntico local.** Dos builds independientes del mismo commit → **mismo SHA-256: `4bcd075edd8ca644652c78ed9243f59251ffa7c835476478ce65e5c8c625fd24`**. Verificación **triple** con los ojos: (a) los dos SHA idénticos (criterio real del Acta, no solo "diffoscope sin diffs"); (b) `/squashfs.sort` NO queda en la ISO; (c) los `.bin` de APT NO quedan en la ISO. Manifiestos de paquetes idénticos. **PR #8** (esperando revisión/merge de Alejandro).
2. **La reproducibilidad tenía TRES capas, no una** (cada una enmascaraba a la siguiente; se destaparon en orden):
   - **ADR-001 — compresión** xz single-thread (`-processors 1`).
   - **ADR-002 — orden** de empaquetado (sortfile completo de 12 708 entradas en orden `LC_ALL=C` + `-sort` nativo de live-build).
   - **ADR-003 — caché APT** desactivado (`Dir::Cache::pkgcache/srcpkgcache` vacíos + `rm` de los `.bin`; APT los reserializaba en cada build y no los cubría `SOURCE_DATE_EPOCH`).
3. **Lección de método grabada:** el diagnóstico de 1C.2 creía que el orden era la última causa; la realidad tenía dos capas. Lo que destapó la segunda fue **verificar contenido fichero a fichero, no solo `-lls`**. Criterio real cumplido: *hashes iguales*, no "sin diffs".
4. **Evolución del diff (material de sustentación):** ~64 MB (orden roto) → ~1 MB (orden cerrado) → 2 ficheros (caché APT) → **0 (MATCH)**.

**⚠️ Estado ahora mismo (dónde retomar):** El jefe de nivel de reproducibilidad está cerrado **a nivel local**. **NO es toda la reproducibilidad todavía** — quedan dos piezas previstas, ninguna es jefe de nivel, pero el criterio del Acta ("verificado por un tercero") las pide:
- **1C.4 — comparación bit-idéntica en CI:** que dos runners *distintos* de GitHub Actions produzcan el mismo SHA. Convierte "funciona en mi máquina" en "verificable por un tercero" (letra del Acta).
- **1C.5 — anclar `snapshot.debian.org`:** hoy los paquetes salieron idénticos por timing; anclar versiones hace el MATCH robusto **en el tiempo** (mismo commit dentro de un mes → mismo hash).
Además, sigue sin cerrar el **Design Partner (D2)**.

---

## 0. ⚠️ DÓNDE QUEDAMOS — LEER PRIMERO PARA RETOMAR

**Fase 1: Pasos 0, 1A, 1B en `main`. 🏆 Reproducibilidad bit-idéntica LOCAL lograda (1C.3, PR #8 esperando merge). Falta el tramo de robustez de 1C (CI + anclaje).**

**Decidido y fijado:**
- Equipo: **Juan José** (@Duque-Londono — build+repro+CLI) + **Alejandro** (@Alejandro-murillo — seguridad/Core OS). Mateo fuera.
- **Deadline: 3 meses duros, sin holgura.** La documentación se entrega a los instructores **una semana antes** de la entrega final → no hay renegociación de criterios; el listón es el del Acta (ISO bit-a-bit verificada por un tercero).
- **Repo:** `teamlocknet/nimbo` público, `main` protegida.
- **Build:** live-build en contenedor Debian bookworm; paridad dev/CI; ISO mínima 260 MB que arranca a login.
- **Reproducibilidad LOCAL: ✅ MATCH bit-idéntico** (SHA `4bcd075e…25fd24`), tres ADRs (compresión + orden + caché APT).
- Método: por secciones → nueva versión del maestro. **Briefs = handoffs entre compañeros; prompts = ciclo con Claude Code.** Ritmo iterativo: **maratoncita a maratoncita**, un PR por vuelta; con pocos tokens se actualiza el maestro antes de cortar.
- **Codename `nimbo`** (desechable, un slug).

**Lo inmediato:**
1. **Merge de PR #8** (squashfs reproducible) cuando Alejandro esté.
2. **1C.4 — comparación bit-idéntica en CI** (dos runners → mismo SHA): cierra el "verificado por un tercero" del Acta.
3. **1C.5 — anclar `snapshot.debian.org`** para robustez temporal del MATCH.
4. **Vía B (Alejandro):** primer `.deb` de `nimbo-net` + inventario de hardening.
5. **Cerrar Design Partner (D2).**

**Los 3 jefes de nivel (§10):** reproducibilidad bit a bit (**✅ local — falta CI+anclaje**) · Design Partner · LUKS + TPM 2.0.

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

**Build/reproducibilidad (materializado en 1A/1B/1C):** live-build corre **dentro** de un contenedor `debian:bookworm-slim` (anclado por digest). Un solo `build-in-container.sh` sirve local (podman rootful) y CI (docker) cambiando `CONTAINER_ENGINE` → **paridad dev/CI**. **Reproducibilidad LOCAL lograda** por la terna: `SOURCE_DATE_EPOCH` + compresión single-thread (ADR-001) + orden de empaquetado por sortfile (ADR-002) + caché APT desactivado (ADR-003). Arnés de medición en `repro/` (build ×2 + diffoscope). Pendiente: verificación en CI (1C.4) y anclaje de versiones (1C.5).

## 5. Los módulos — mapa de trabajo, dueños y palanca de IA

| Módulo | Dueño | Palanca de IA | Riesgo | Estado |
|---|---|---|---|---|
| ISO live-build + Xfce4 endurecido | Juan José | Media | Medio | ISO mínima ✅; falta Xfce4/hardening |
| CI/CD + repo APT + releases firmados | Juan José | Alta | Medio | CI compila ISO ✅; falta APT/releases |
| **Reproducibilidad bit a bit** | **Juan José** | **Baja** (empírico) | **Muy alto** | **🏆 MATCH local ✅; falta CI (1C.4) + anclaje (1C.5)** |
| **CLI de auditoría** | **Juan José** | **Muy alta** | Bajo | Pendiente |
| Hardening + navegadores + Tor | Alejandro | Media-alta | Medio | Pendiente |
| VPN P2P + `nimbo-net join` | Alejandro | Alta | Bajo | Pendiente |
| LUKS + TPM 2.0 (swtpm) | Alejandro | Media | Medio-alto | Pendiente |
| Air-gapped (`nimbo-update-offline`) | Alejandro | Media-alta | Bajo | Pendiente |
| QA / benchmarks RAM / smoke tests | Compartido (CI) | Alta | Medio | Validación de ISO ✅ base |
| Docs, ADRs, documento maestro | Compartido + orquestador | Muy alta | Bajo | Al día (v1.5); ADR-000/001/002/003 |

## 6. Stack

Debian Stable + **live-build** (en contenedor) · Xfce4 · **Python 3 / Typer** · **GitHub Actions** + **Pages** · **aptly** · **WireGuard** vía **Tailscale** (o Headscale) · **Calamares** · **LUKS + systemd-cryptenroll + TPM 2.0** (**swtpm**) · **QEMU/KVM** headless · **GPG** · **diffoscope** · **podman/docker** · **Git**. Todo FOSS, infra **$0**.

## 7. Método de trabajo

- **Roles:** **chat ORQUESTA** (piensa, escribe prompts maestros, revisa, mantiene este doc; no escribe código del producto) · **Claude Code programa** · **el equipo ejecuta, decide, verifica con los ojos** y hace lo del mundo físico (permisos, repo, **operaciones privilegiadas/sudo**, hardware/TPM, Design Partner).
- **Briefs vs prompts:** briefs = handoffs entre los dos compañeros; Claude Code se dirige por prompts (prompt maestro → PLAN → revisión → aprobación por prompt). Claude Code **se detiene en bloqueadores** sin inventar (validado en todos los pasos; en 1C corrigió supuestos falsos de su propio plan antes de codificar — checkpoint funcionando).
- **Ritmo iterativo (1C):** maratoncita a maratoncita — un PR por vuelta del bucle medir→cerrar→medir; se para, se analiza; con pocos tokens se actualiza el maestro antes de cortar.
- **Contrato anti-choque:** cada componente consume el output del otro **por referencia**, nunca edita a través de fronteras. CODEOWNERS + `main` protegida + ramas `iniciales/tema` + PRs pequeños.
- **Reproducibilidad desde el día 1** · **ritual de cierre** (CI verde + verificación con los ojos + commit + push + release firmado en hitos) · **corrección** (test rojo primero) · **checkpoint en el núcleo** (esquema/pipeline/PCR/hardening/receta → parar y preguntar) · **no modelar sobre resúmenes** (probar, no suponer — validado en 1C con `-no-exports`, los manifiestos y la verificación fichero-a-fichero) · **"compiló" ≠ "es reproducible"; MATCH = hashes iguales, no "sin diffs"** · **no decidir seguridad cansado.**

### Principios no negociables
1. **REPRODUCIBILIDAD VERIFICABLE.** 2. **HERMETISMO.** 3. **COSTO CERO / TODO FOSS AUDITABLE.** 4. **EVIDENCIA CON HASH.** 5. **EL DETERMINISMO PRIMERO.** 6. **VERIFICAR CON LOS OJOS.** 7. **CHECKPOINT EN EL NÚCLEO.**

## 8. Plan de fases (13 semanas — guía; la Vía A va por la columna del build)

| Sem | Sección / Foco | Entregable "verde" | Estado |
|---|---|---|---|
| 1 | **Columna del build:** 1A ISO mínima · 1B CI compila · 1C reproducibilidad | ISO en `main` + CI + MATCH | 🟢 1A ✅ · 1B ✅ · 🏆 **1C.1–1C.3 ✅ (MATCH local)** · falta 1C.4/1C.5 |
| 2 | CLI `init` + logging | `init` | ⬜ |
| 3 | CLI `capture` (SHA-256) + hardening base Xfce4 (<500 MB) | Evidencia + RAM | ⬜ |
| 4 | CLI `report` (MD→PDF) + Calamares | CLI completo + ISO instalable | ⬜ |
| 5 | Navegador endurecido + Tor + detección de fugas | Navegación | ⬜ |
| 6 | VPN P2P + `nimbo-net join` + docs local | CU-04 y RF-07 | ⬜ (Vía B arranca antes, en paralelo) |
| 7 | Air-gapped (`nimbo-update-offline` + GPG) | RF-CORE-06 | ⬜ |
| 8 | LUKS+TPM en QEMU+swtpm + flujo passphrase | RF-CORE-05 en QEMU | ⬜ |
| 9 | Reproducibilidad bit-idéntica entre 2 runners | RNF-SEC-07 | 🟢 **local hecho; CI = 1C.4** |
| 10 | Repo APT (aptly+Pages) + releases firmados | Distribución + release 1 | ⬜ |
| 11 | QA + benchmarks + **auditoría Design Partner** | Hallazgos | ⬜ |
| 12 | ≥70% hallazgos + validación hardware real (TPM) + release final | ISO v1.0 firmada | ⬜ |
| 13 | Docs finales + ensayo de sustentación | Sustentación lista | ⬜ |

**Nota de secuencia:** la columna del build (1A→1B→1C) va primero, adelantando la reproducibilidad. El CLI y lo demás vienen después; Vía B (Alejandro) en paralelo cuando se libere.

## 9. Registro de ejecución

**Fase 0 — Fundación (CERRADA ✅):** v1.0 → v1.1.

**Fase 1 — Paso 0: Cimientos (CERRADO ✅, PR #1).** **Paso 1A: ISO mínima booteable (CERRADO ✅, PR #2)** — 260 MB, arranca a login; aprendizajes: build rootful en Fedora, `--network=host`, Enter al menú isolinux. **Paso 1B: CI compila la ISO (CERRADO ✅, PR #3)** — paridad dev/CI, digest anclado, validación que revienta el job, artifact.

**Fase 1 — Paso 1C: Reproducibilidad bit a bit:**
- **1C.1 — Diagnóstico (✅, PR #5, mergeado):** arnés `build-twice.sh` + `diff-isos.sh`; diferencia aislada a ~4 bytes; causa = xz multihilo.
- **1C.2 — Compresión (✅, PR #6, mergeado):** single-thread `-processors 1` (ADR-001). Necesario, no suficiente; destapó el residual de orden.
- **1C.3 — Orden + caché APT → 🏆 MATCH (✅ CERRADO, PR #8 esperando merge):**
  - Orden de empaquetado cerrado con **sortfile completo** (12 708 entradas, `LC_ALL=C`) vía `-sort` nativo de live-build (ADR-002). Diagnóstico verificado leyendo el diff real (tablas del superbloque corridas 12 bytes + bloque de datos a ~64 MB) y el fuente de live-build/squashfs-tools.
  - Residual final destapado: **caché binario de APT** (`pkgcache.bin`/`srcpkgcache.bin`) que APT reserializa en cada build. Cerrado desactivando el caché (`apt.conf.d/99nimbo-reproducible`) + `rm` (ADR-003). *Un `rm` solo no bastaba: la etapa binary los regenera.*
  - **Verificación triple con los ojos:** los dos SHA idénticos (`4bcd075e…25fd24`) · `/squashfs.sort` fuera de la ISO · `.bin` de APT fuera de la ISO · manifiestos idénticos.
  - Corrección de proceso en el camino: Claude Code detectó que un supuesto de su plan aprobado (que `/squashfs.sort` quedaba en la ISO) era falso en `with_chroot=true`, y paró a corregir antes de commitear un ADR con rationale falso. Decisión tomada: **no** añadir `excludes` (sería no-op hoy; superficie mínima), documentado en ADR-002.
- **1C.4 — Comparación bit-idéntica en CI (SIGUIENTE):** dos runners distintos de Actions → mismo SHA. Cierra el "verificado por un tercero" del Acta.
- **1C.5 — Anclaje `snapshot.debian.org` (SIGUIENTE):** robustez temporal del MATCH.

**Estado de git:** `main` = Paso 0 + 1A + 1B + 1C.1 + 1C.2. Abierto: **PR #8** (1C.3, MATCH) esperando merge de Alejandro. Pendiente: PR del maestro v1.5.

## 10. Los 3 jefes de nivel + palanca de IA

**Palanca:** la IA colapsa "código que escribimos"; **casi no toca** "sistemas que hay que observar". El 24/7 va a lo segundo; las máquinas potentes fueron la palanca real de 1C (más builds/hora = más vueltas del bucle).

1. **Reproducibilidad bit a bit (RNF-SEC-07) — 🏆 LOCAL LOGRADA.** Cerrado: higiene determinista, digest de imagen base, paridad dev/CI, y la terna compresión+orden+caché APT → **MATCH bit-idéntico**. **Falta (no jefe de nivel, pero pedido por el Acta):** 1C.4 comparación en CI (verificación por tercero) y 1C.5 anclaje `snapshot.debian.org` (robustez temporal). **Distinción clave:** logramos "*nuestro pipeline* es determinista"; "todo Debian aguas arriba" sigue fuera de alcance y nadie lo exige.
2. **Design Partner (D2)** — riesgo logístico puro; **sigue sin cerrar.**
3. **LUKS + TPM 2.0** — swtpm cubre QEMU; PCR se rompe con updates de kernel. Meta: receta validada en QEMU+swtpm; hardware real como extra.

## 11. Recursos y costo cero

Escaso: tiempo y expertise, no dinero. Infra $0 (GitHub público + Actions + Pages, Tailscale free, FOSS). No monetario: build ~6 min (holgado) + **una máquina con TPM 2.0 real** para la semana 12. Curva de live-build: domada a lo largo de 1A/1B/1C.

## 12. Decisiones abiertas y pendientes

| # | Ítem | Estado |
|---|---|---|
| D1 | **Nombre real del proyecto** | 🔴 Abierto (codename `nimbo` cubre el interín) |
| D2 | **Cerrar Design Partner** (o plan B) | 🔴 **Sigue abierto** |
| D3 | Reconciliar cronograma | ✅ 3 meses duros, sin holgura |
| D4 | Actualizar docs SENA a 2 personas | 🟠 Antes de la entrega final |
| D5 | Renegociar criterio de reproducibilidad | ⚫ Cerrada: NO se renegocia (doc a 1 semana de la entrega; listón = Acta) |
| D6 | Owner de Python del CLI | ✅ Juan José |
| D7 | Codename provisional | ✅ `nimbo` |
| D8 | Por cuál vía arranca Juan José | ✅ Build (columna 1A→1B→1C) |
| D9 | Qué Debian Stable se envía finalmente | 🟠 bookworm fijado; formalizar en ADR |

## 13. Riesgos y deuda

- **Cronograma:** 13 semanas duras; cero margen. *Mitigante grande:* el jefe de nivel más peligroso (reproducibilidad) ya está resuelto a nivel local, muy temprano.
- **Técnico:** reproducibilidad (🏆 local hecho; falta CI+anclaje, bajo riesgo), TPM/PCR (medio-alto), tamaño en gama baja (bajo — 260 MB).
- **Logístico:** Design Partner sin cerrar (alto).
- **Deuda menor (no urgente):** warning de deprecación de Node 20 en las actions — limpiar cuando salgan versiones nuevas.

---

*v1.5 — Hoy el gigante cayó. Dos discos nacidos del mismo commit, compilados por separado, resultaron gemelos hasta el último bit: `4bcd075e…25fd24`, dos veces, sin una sola diferencia. Lo que empezó como el requisito que más miedo daba —el que nos hizo elegir este proyecto— es ahora la prueba más sólida de que sabemos lo que hacemos. Y no cayó de un golpe de suerte: cayó capa por capa, como una cebolla que llora al pelarla. Primero la compresión, que cambiaba según cuántos hilos corrían. Debajo, el orden en que se recogen los archivos de una carpeta, que nadie garantiza. Y debajo de ese, escondido hasta que quitamos los dos de encima, un caché de APT que se reescribía a sí mismo en cada build. Tres máscaras, tres ADRs, y en cada vuelta el mismo ritual: medir de verdad, no adivinar; verificar con los ojos, no con la fe; y cuando un supuesto resultó falso a mitad de camino, parar y corregirlo en vez de seguir de largo. El diff que empezó pesando sesenta y cuatro megas terminó en cero. Falta poco para que esta victoria sea también "verificable por un tercero" —llevarla a dos runners de la nube— y para blindarla contra el paso del tiempo. Pero eso es pulir una medalla que ya ganamos. Esta noche se guarda entera: el sistema no solo arranca, ahora se puede reconstruir idéntico, y eso —en un mundo que desconfía de lo que no puede auditar— es la carta de presentación más honesta que un equipo puede firmar.*
