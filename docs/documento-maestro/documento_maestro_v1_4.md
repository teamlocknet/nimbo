# ⟨NOMBRE POR DEFINIR · codename `nimbo`⟩ — Documento maestro del proyecto
## Ecosistema / sistema operativo de ciberseguridad basado en Debian

**Versión:** 1.4 (Fase 1: 🔴 **PASO 1C EN CURSO — el jefe de nivel, muy cerca de caer.** El no-determinismo de la ISO bajó de "toda la compresión" a **~12 bytes por el orden de empaquetado del squashfs**. Falta una maratoncita (1C.3) para el MATCH.)
**Grupo:** LockNet · **Repo:** `github.com/teamlocknet/nimbo` (público) · **Contexto:** Proyecto de grado — SENA, ADSO
**Fecha:** Septiembre 2026
**Estado:** 🟢 **EN MARCHA.** 2 personas + IA · **13 semanas duras** (sep → dic 2026, sin holgura) · 24/7 · dev en máquinas potentes → target gama baja · alcance **COMPLETO**. Vía A (build+reproducibilidad) de Juan José avanzando fuerte; Vía B (Alejandro) aún sin arrancar.

**Cambios frente a v1.3:**
1. **Paso 1C.1 CERRADO (diagnóstico) — PR #5** (arnés, *en espera de merge de Alejandro*). Se montó el arnés de reproducibilidad (`repro/build-twice.sh` + `diff-isos.sh` con diffoscope en contenedor). Primer diagnóstico **nítido**: dos builds del mismo commit difieren en **~4 bytes** dentro de `filesystem.squashfs`; **manifiestos de paquetes idénticos** (0% ruido de versiones, probado no supuesto) → 100% intrínseco del pipeline. Causa: **compresión xz multihilo** de mksquashfs.
2. **Paso 1C.2 EN CURSO (compresión) — PR #6** (*en espera de merge; se le apilará 1C.3 encima*). Se fijó **compresión single-thread** determinista vía el punto de extensión oficial de live-build (`MKSQUASHFS_OPTIONS="-processors 1"` en `auto/build`), documentado en **ADR-001**. **Verificado:** single-thread es determinista dada una entrada fija; multihilo descartado como causa; `-no-exports` descartado probándolo. **Resultado honesto:** el single-thread era necesario pero **no suficiente** — sigue en DIFFER (~12 bytes). Impacto en tiempo: trivial (build completo ~5m50s vs timeout de 40m; no tocar el timeout). `build-iso` de CI verde con la receta nueva.
3. **Residual descubierto detrás → 1C.3:** el segundo no-determinismo, antes tapado por el xz, es el **orden de `readdir`** con que mksquashfs empaqueta los directorios (varía entre dos debootstrap). Contenido, permisos, mtimes y orden lógico idénticos.

**⚠️ Estado ahora mismo (dónde retomar):** El jefe de nivel está a **una maratoncita** de caer. **Siguiente: Paso 1C.3 — forzar orden determinista en el empaquetado del squashfs** (típicamente alimentar a mksquashfs una entrada ordenada, p. ej. `find | sort` / sortfile / modo tar) y volver a medir con el mismo arnés → **objetivo: MATCH.** 1C.3 se construye **encima de la rama de #6** (`jj/repro-squashfs-determinista`), no desde main; el ADR-001 cubrirá compresión + orden como "lo que hizo falta para que el squashfs sea determinista". Sin cerrar: **Design Partner (D2)**.

**Nota de PRs abiertos (esperando a Alejandro):** #5 (arnés) y #6 (squashfs determinista). Orden de merge sugerido: **#5 primero, luego #6.** Además, el maestro v1.3 → v1.4 debe subirse por su PR.

---

## 0. ⚠️ DÓNDE QUEDAMOS — LEER PRIMERO PARA RETOMAR

**Fase 1: Pasos 0, 1A, 1B en `main`. Paso 1C (reproducibilidad, el jefe de nivel) EN CURSO — a una maratoncita del MATCH.**

**Decidido y fijado:**
- Equipo: **Juan José** (@Duque-Londono — build+repro+CLI) + **Alejandro** (@Alejandro-murillo — seguridad/Core OS). Mateo fuera.
- **Deadline: 3 meses duros, sin holgura.** *(Nota: la documentación se entrega a los instructores una semana antes de la entrega final; no hay renegociación de criterios — el listón es el del Acta: ISO bit-a-bit verificada por un tercero.)*
- **Repo:** `teamlocknet/nimbo` público, `main` protegida.
- **Build:** live-build en contenedor Debian bookworm; paridad dev/CI; ISO mínima 260 MB que arranca a login.
- **Reproducibilidad:** arnés de medición operativo; xz multihilo cerrado; **falta el orden del squashfs**.
- Método: por secciones → nueva versión del maestro. **Briefs = handoffs entre compañeros; prompts = ciclo con Claude Code.** Ritmo de 1C: **maratoncita a maratoncita** — un PR por vuelta, se para, se analiza, y con pocos tokens se actualiza el maestro.
- **Codename `nimbo`** (desechable, un slug).

**Lo inmediato:**
1. **Paso 1C.3 (Vía A) — rematar el jefe de nivel:** orden determinista del squashfs → medir → **MATCH esperado**. Encima de la rama de #6.
2. **Merge de PRs pendientes** cuando Alejandro esté: #5 (arnés) → #6 (squashfs determinista + 1C.3) → PR del maestro v1.4.
3. **Vía B (Alejandro), cuando se libere:** primer `.deb` de `nimbo-net` + inventario de hardening.
4. **Cerrar Design Partner (D2).**

**Los 3 jefes de nivel (§10):** reproducibilidad bit a bit (**a una maratoncita**) · Design Partner · LUKS + TPM 2.0.

---

## 1. Identidad del proyecto

| | |
|---|---|
| **LockNet** | El grupo/colectivo (org GitHub `teamlocknet`). Autor y destinatario de la credibilidad pública. |
| **⟨producto — NOMBRE POR DEFINIR⟩** | El SO que se entrega. **Decisión abierta.** Candidatos heredados: *VELDORA* / *NEXUS Security OS*. |
| **`nimbo`** | **Codename interno desechable** + slug canónico. |

**Convención de nombre:** un **único slug `nimbo`** en TODO → el nombre real entra con **un find-and-replace global**. **Naming heredado a unificar** (VELDORA/NEXUS mezclados en docs SENA) al decidir el nombre. Contexto: proyecto de grado SENA (ADSO); criterios de éxito en Acta §13.

## 2. El producto en una frase

*"Un sistema operativo de auditoría basado en Debian Stable que un equipo de ciberseguridad instala y usa el mismo día — navegación endurecida, red privada del propio equipo y trazabilidad de auditorías con evidencia verificable por hash — todo offline, reproducible bit a bit y sin una sola línea de telemetría."*

## 3. Alcance — qué es y qué NO es

**SÍ (todos, v1.0):** Core OS endurecido (ISO live+instalable, Debian+Xfce4, <500 MB idle) · navegación segura (endurecido tipo LibreWolf + puente Tor con detección de fugas) · red aislada (VPN P2P WireGuard/Tailscale bajo demanda) · CLI de auditoría (`init`/`capture`/`report`) · seguridad transversal (reproducibilidad bit a bit, LUKS+TPM 2.0, air-gapped con GPG) · distribución (CI/CD, repo APT propio, releases firmados, ADRs).

**NO:** kernel propio, 32 bits, infra de pago, y — deliberadamente — **cualquier IA dentro del producto.**

**⚠️ Doble plano de la IA:** el **producto** no lleva IA (diseño); el **desarrollo** sí la usa. Construir *con* IA algo que *no contiene* IA no es contradicción — decirlo explícito en la sustentación.

## 4. Arquitectura de software

3 capas (DAS v2.0): **Capa 1** Debian Stable + systemd · **Capa 2** Xfce4 optimizado · **Capa 3** scripts Python 3 (CLI de auditoría + `nimbo-net`). **Patrones del CLI:** Command + Repository. Estructura del monorepo/CLI/engagement: §4.1–4.3 de v1.1, en `main`.

**Build/reproducibilidad (materializado en 1A/1B/1C):** live-build corre **dentro** de un contenedor `debian:bookworm-slim` (anclado por digest). Un solo `build-in-container.sh` sirve local (podman rootful) y CI (docker) cambiando `CONTAINER_ENGINE` → **paridad dev/CI**. Reproducibilidad: `SOURCE_DATE_EPOCH` + compresión squashfs single-thread (ADR-001) + **pendiente: orden determinista del empaquetado**. Arnés de medición en `repro/` (build ×2 + diffoscope).

## 5. Los módulos — mapa de trabajo, dueños y palanca de IA

| Módulo | Dueño | Palanca de IA | Riesgo | Estado |
|---|---|---|---|---|
| ISO live-build + Xfce4 endurecido | Juan José | Media | Medio | ISO mínima ✅; falta Xfce4/hardening |
| CI/CD + repo APT + releases firmados | Juan José | Alta | Medio | CI compila ISO ✅; falta APT/releases |
| **Reproducibilidad bit a bit** | **Juan José** | **Baja** (empírico) | **Muy alto** | **En curso (1C) — a 1 maratoncita del MATCH** |
| **CLI de auditoría** | **Juan José** | **Muy alta** | Bajo | Pendiente |
| Hardening + navegadores + Tor | Alejandro | Media-alta | Medio | Pendiente |
| VPN P2P + `nimbo-net join` | Alejandro | Alta | Bajo | Pendiente |
| LUKS + TPM 2.0 (swtpm) | Alejandro | Media | Medio-alto | Pendiente |
| Air-gapped (`nimbo-update-offline`) | Alejandro | Media-alta | Bajo | Pendiente |
| QA / benchmarks RAM / smoke tests | Compartido (CI) | Alta | Medio | Validación de ISO ✅ base |
| Docs, ADRs, documento maestro | Compartido + orquestador | Muy alta | Bajo | Al día (v1.4); ADR-000, ADR-001 |

## 6. Stack

Debian Stable + **live-build** (en contenedor) · Xfce4 · **Python 3 / Typer** · **GitHub Actions** + **Pages** · **aptly** · **WireGuard** vía **Tailscale** (o Headscale) · **Calamares** · **LUKS + systemd-cryptenroll + TPM 2.0** (**swtpm**) · **QEMU/KVM** headless · **GPG** · **diffoscope** · **podman/docker** · **Git**. Todo FOSS, infra **$0**.

## 7. Método de trabajo

- **Roles:** **chat ORQUESTA** (piensa, escribe prompts maestros, revisa, mantiene este doc; no escribe código del producto) · **Claude Code programa** · **el equipo ejecuta, decide, verifica con los ojos** y hace lo del mundo físico (permisos, repo, **operaciones privilegiadas/sudo**, hardware/TPM, Design Partner).
- **Briefs vs prompts:** briefs = handoffs entre los dos compañeros; Claude Code se dirige por prompts (prompt maestro → PLAN → revisión → aprobación por prompt). Claude Code **se detiene en bloqueadores** sin inventar (validado en todos los pasos).
- **Ritmo iterativo (1C):** maratoncita a maratoncita — un PR por vuelta del bucle medir→cerrar→medir; se para, se analiza; con pocos tokens se actualiza el maestro antes de cortar.
- **Contrato anti-choque:** cada componente consume el output del otro **por referencia**, nunca edita a través de fronteras. CODEOWNERS + `main` protegida + ramas `iniciales/tema` + PRs pequeños.
- **Reproducibilidad desde el día 1** · **ritual de cierre** (CI verde + verificación con los ojos + commit + push + release firmado en hitos) · **corrección** (test rojo primero) · **checkpoint en el núcleo** (esquema/pipeline/PCR/hardening/receta → parar y preguntar) · **no modelar sobre resúmenes** (probar, no suponer — validado en 1C con `-no-exports` y los manifiestos) · **"compiló" ≠ "es reproducible"** · **no decidir seguridad cansado.**

### Principios no negociables
1. **REPRODUCIBILIDAD VERIFICABLE.** 2. **HERMETISMO.** 3. **COSTO CERO / TODO FOSS AUDITABLE.** 4. **EVIDENCIA CON HASH.** 5. **EL DETERMINISMO PRIMERO.** 6. **VERIFICAR CON LOS OJOS.** 7. **CHECKPOINT EN EL NÚCLEO.**

## 8. Plan de fases (13 semanas — guía; la Vía A va por la columna del build)

| Sem | Sección / Foco | Entregable "verde" | Estado |
|---|---|---|---|
| 1 | **Columna del build:** 1A ISO mínima · 1B CI compila · 1C reproducibilidad | ISO en `main` + CI + MATCH | 🟢 1A ✅ · 1B ✅ · 🔴 **1C en curso (1C.1✅ 1C.2✅ → 1C.3)** |
| 2 | CLI `init` + logging | `init` | ⬜ |
| 3 | CLI `capture` (SHA-256) + hardening base Xfce4 (<500 MB) | Evidencia + RAM | ⬜ |
| 4 | CLI `report` (MD→PDF) + Calamares | CLI completo + ISO instalable | ⬜ |
| 5 | Navegador endurecido + Tor + detección de fugas | Navegación | ⬜ |
| 6 | VPN P2P + `nimbo-net join` + docs local | CU-04 y RF-07 | ⬜ (Vía B arranca antes, en paralelo) |
| 7 | Air-gapped (`nimbo-update-offline` + GPG) | RF-CORE-06 | ⬜ |
| 8 | LUKS+TPM en QEMU+swtpm + flujo passphrase | RF-CORE-05 en QEMU | ⬜ |
| 9 | Reproducibilidad bit-idéntica entre 2 runners | RNF-SEC-07 | 🟡 **adelantada** (se ataca en 1C) |
| 10 | Repo APT (aptly+Pages) + releases firmados | Distribución + release 1 | ⬜ |
| 11 | QA + benchmarks + **auditoría Design Partner** | Hallazgos | ⬜ |
| 12 | ≥70% hallazgos + validación hardware real (TPM) + release final | ISO v1.0 firmada | ⬜ |
| 13 | Docs finales + ensayo de sustentación | Sustentación lista | ⬜ |

**Nota de secuencia:** la columna del build (1A→1B→1C) se hace primero, adelantando la reproducibilidad. El CLI y lo demás vienen después; Vía B (Alejandro) en paralelo cuando se libere.

## 9. Registro de ejecución

**Fase 0 — Fundación (CERRADA ✅):** v1.0 → v1.1 (codename + modelado de estructura).

**Fase 1 — Paso 0: Cimientos (CERRADO ✅):** repo + estructura §4 + CODEOWNERS + ADR-000 + CI `estructura` + `main` protegida (**PR #1**).

**Fase 1 — Paso 1A: ISO mínima booteable (CERRADO ✅, PR #2):** live-build (Debian 12 bookworm), 260 MB, arranca a `nimbo-live login:` en QEMU. Aprendizajes: build rootful en Fedora, `--network=host`, Enter al menú isolinux. Higiene de reproducibilidad aplicada.

**Fase 1 — Paso 1B: CI compila la ISO (CERRADO ✅, PR #3):** workflow `build-iso.yml`, paridad dev/CI (`CONTAINER_ENGINE`), imagen base por digest, ISO de CI = mismo conteo de bytes que la local, validación que revienta el job, artifact descargable.

**Fase 1 — Paso 1C: Reproducibilidad bit a bit (EN CURSO 🔴):**
- **1C.1 — Diagnóstico (CERRADO ✅, PR #5, en espera de merge):** arnés `repro/build-twice.sh` + `diff-isos.sh`. Veredicto DIFFER con diferencia **aislada a ~4 bytes** del squashfs; manifiestos de paquetes **idénticos** (probado, enfoque data-driven); causa = **xz multihilo**. `sha256sum.txt` = cascada.
- **1C.2 — Compresión determinista (EN CURSO, PR #6, en espera de merge):** `MKSQUASHFS_OPTIONS="-processors 1"` vía punto de extensión oficial de live-build (`auto/build`), **ADR-001** (con nota de reversibilidad). Single-thread verificado determinista de forma aislada; multihilo y `-no-exports` descartados probándolos. **Sigue DIFFER (~12 bytes):** necesario pero no suficiente. Tiempo build ~5m50s (holgado vs timeout 40m). `build-iso` de CI verde.
- **1C.3 — Orden determinista del squashfs (SIGUIENTE 🔴):** causa residual = **orden de `readdir`** al empaquetar; solución típica = alimentar a mksquashfs una entrada ordenada. Se apila **sobre la rama de #6**. **Objetivo: MATCH.**

**Estado de git:** `main` = Paso 0 + 1A + 1B. Abiertos (esperando a Alejandro): **PR #5** (arnés), **PR #6** (squashfs determinista, se le suma 1C.3). Pendiente: PR del maestro v1.4. Orden de merge sugerido: #5 → #6 → maestro.

## 10. Los 3 jefes de nivel + palanca de IA

**Palanca:** la IA colapsa "código que escribimos"; **casi no toca** "sistemas que hay que observar". El 24/7 va a lo segundo; las máquinas potentes son la palanca (más builds/hora = más vueltas del bucle 1C).

1. **Reproducibilidad bit a bit (RNF-SEC-07) — EN CURSO, a 1 maratoncita.** Cerrados: higiene determinista, digest de imagen base, paridad dev/CI, xz multihilo. **Falta:** orden del squashfs (1C.3). Deudas futuras (no bloquean el MATCH local): anclar versiones a **snapshot.debian.org** (hoy no hay ruido de versiones), llevar la comparación al CI cuando el MATCH local sea estable. **Distinción clave:** el objetivo es "*mi pipeline* es determinista" (alcanzable, en ataque), no "todo Debian aguas arriba es reproducible" (fuera de alcance).
2. **Design Partner (D2)** — riesgo logístico puro; **sigue sin cerrar.**
3. **LUKS + TPM 2.0** — swtpm cubre QEMU; PCR se rompe con updates de kernel. Meta: receta validada en QEMU+swtpm; hardware real como extra.

## 11. Recursos y costo cero

Escaso: tiempo y expertise, no dinero. Infra $0 (GitHub público + Actions + Pages, Tailscale free, FOSS). No monetario: build ~6 min (holgado) + **una máquina con TPM 2.0 real** para la semana 12. Curva de live-build: mayormente domada en 1A/1B/1C.

## 12. Decisiones abiertas y pendientes

| # | Ítem | Estado |
|---|---|---|
| D1 | **Nombre real del proyecto** | 🔴 Abierto (codename `nimbo` cubre el interín) |
| D2 | **Cerrar Design Partner** (o plan B) | 🔴 **Sigue abierto** |
| D3 | Reconciliar cronograma | ✅ 3 meses duros, sin holgura |
| D4 | Actualizar docs SENA a 2 personas | 🟠 Antes de la entrega final |
| D5 | Renegociar criterio de reproducibilidad | ⚫ **Cerrada: NO se renegocia** — la doc se entrega 1 semana antes; el listón es el del Acta |
| D6 | Owner de Python del CLI | ✅ Juan José |
| D7 | Codename provisional | ✅ `nimbo` |
| D8 | Por cuál vía arranca Juan José | ✅ Build (columna 1A→1B→1C) |
| D9 | Qué Debian Stable se envía finalmente | 🟠 bookworm fijado para el ladrillo; formalizar en ADR |

## 13. Riesgos y deuda

- **Cronograma:** 13 semanas duras; cero margen. *Mitigante:* adelantar la reproducibilidad baja el riesgo de la semana 9.
- **Técnico:** reproducibilidad bit-idéntica (alto, **a 1 maratoncita del MATCH**), TPM/PCR (medio-alto), tamaño en gama baja (bajo — 260 MB, holgado).
- **Logístico:** Design Partner sin cerrar (alto).
- **Deuda menor (no urgente):** warning de deprecación de Node 20 en las actions — limpiar cuando salgan versiones nuevas.

---

*v1.4 — El monstruo que más temíamos resultó tener cara, y hoy le vimos la segunda. Cuando pusimos los dos discos frente al espejo, no eran mil diferencias ni un abismo: eran cuatro bytes, todos en un solo lugar, el corazón comprimido del sistema. Le quitamos la primera máscara —la compresión que cambiaba según cuántos hilos corrían a la vez— y, como pasa con las cosas difíciles hechas en serio, detrás había otra más callada: el orden en que el sistema recoge los archivos de una carpeta, que nadie garantiza igual dos veces. No es un retroceso; es el arnés haciendo su trabajo, destapando una a una las capas que estaban escondidas. La diferencia pasó de "toda la compresión" a doce bytes de orden. Y aprendimos a no creerle a las corazonadas: probamos que el hilo único era determinista, probamos que no era la tabla de exportación, medimos el tiempo para saber que no rompíamos nada. El gigante ya casi no respira. Falta una maratoncita —enseñarle al empaquetador a recoger siempre en el mismo orden— y entonces, por fin, dos discos nacidos del mismo commit deberían ser gemelos idénticos hasta el último bit. Paramos aquí, con la bitácora al día y las fuerzas guardadas, para darle el golpe final con la cabeza fresca. El MATCH se merece una sesión limpia.*
