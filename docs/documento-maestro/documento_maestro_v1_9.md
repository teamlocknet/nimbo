# ⟨NOMBRE POR DEFINIR · codename `nimbo`⟩ — Documento maestro del proyecto
## Ecosistema / sistema operativo de ciberseguridad basado en Debian

**Versión:** 1.9 (Fase 1: reproducibilidad (1C) completa · CLI (2A-2C) completo · **Core OS: el escritorio Xfce4 mínimo ya arranca en la ISO a 368 MiB idle (3A)**. Además se cerró un no-determinismo latente que venía desde 1A. Falta: hardening de seguridad (3B), integrar CLI/navegadores/VPN a la ISO, y el resto de la Vía B.)
**Grupo:** LockNet · **Repo:** `github.com/teamlocknet/nimbo` (público) · **Contexto:** Proyecto de grado — SENA, ADSO
**Fecha:** Septiembre 2026
**Estado:** 🟢 **EN MARCHA, con buen ritmo.** 2 personas + IA — **Alejandro temporalmente no disponible; su bloque más urgente (Core OS endurecido) lo asumió Juan José** (que también es experto en ciberseguridad). 13 semanas duras (sep → dic 2026, sin holgura) · 24/7 · dev en máquinas potentes → target gama baja · alcance **COMPLETO**.

**Cambios frente a v1.8:**
1. **D13 — Traslado temporal de responsabilidades.** Alejandro no puede trabajar por ahora. Su bloque **más urgente** (el "Core OS endurecido" — Módulo 1 del DAS: hardening + Xfce4) pasa a **Juan José**, porque es el cuello de botella que permite ensamblar el producto (los pilares hechos aún no están *dentro* de la ISO). Juan José también domina ciberseguridad, así que no es terreno ajeno. Alejandro **conserva** VPN P2P, LUKS+TPM y air-gapped para cuando vuelva.
2. **Paso 3A — Xfce4 mínimo en la ISO + medición de RAM (✅ COMPLETO, PR #17, esperando merge).** El escritorio arranca con **autologin** y la ISO consume **368 MiB en idle** (techo del Acta: <500 MB → **holgado, ~130 MB de colchón**). Los 3 entregables verificados con los ojos (screenshot + RAM + MATCH verde).
3. **Bug de reproducibilidad LATENTE (desde 1A) encontrado y cerrado.** `repro-verify` falló al meter Xfce; `diffoscope` demostró que el payload con Xfce era **bit-idéntico** — el único culpable era `.disk/archive_trace` (traza del mirror que snapshot.debian.org sirve intermitente). **Existía desde 1A y pasaba por suerte.** Xfce no lo causó, lo *destapó*. Cerrado con un hook que normaliza esa traza. (El arnés de 1C convirtió un fallo latente e intermitente en uno visible y arreglable — habría reventado aleatoriamente más adelante.)
4. **Aprendizaje de recipe:** `--apt-recommends false` había dejado fuera a `user-setup`/`sudo` (Recommends de live-config) → sin ellos live-config no creaba el usuario `nimbo` → rompía login y autologin. Fix: declararlos explícitos (mismo patrón quirúrgico de los drivers de X), sin tocar la política de recommends. Diagnosticado inspeccionando el chroot.

**⚠️ Estado ahora mismo (dónde retomar):**
- **Merges pendientes:** **PR #17 (Xfce4/3A) aprobado, esperando merge de Alejandro** — pero **ya no bloquea nada** (3A está cerrado y verificado). Y **este maestro v1.9** por subir (su propio PR).
- **Siguiente frente natural: Paso 3B — hardening de seguridad del sistema base** (sysctl, telemetría off que exige RNF-01, quitar servicios/superficie innecesaria, políticas). Es terreno de experto de Juan José y el ladrillo que sigue sobre el escritorio ya montado. *(Nota de seguridad ya anotada por Claude Code: el autologin de la sesión live es cómodo pero debe revisarse en 3B — un SO de seguridad no debería autologuear sin criterio; decidir política.)*
- **Otros frentes abiertos:** integrar el CLI a la ISO + empaquetarlo `.deb`; navegadores endurecidos + Tor; y el resto de la Vía B de Alejandro (VPN, LUKS+TPM, air-gapped) cuando vuelva.
- **Pendientes con reloj:** Design Partner (D2), decisión D9 (trixie vs bookworm).

---

## 0. ⚠️ DÓNDE QUEDAMOS — LEER PRIMERO PARA RETOMAR

**Fase 1: reproducibilidad (1C) completa · CLI (2A-2C) completo · Core OS con escritorio Xfce4 (3A) completo. Todo en `main` salvo #17 (esperando merge, no bloquea). Empezó el bloque que era de Alejandro, por mano de Juan José (D13).**

**Decidido y fijado:**
- Equipo: **Juan José** (@Duque-Londono — build+repro+CLI, y ahora **Core OS endurecido** por traslado D13) + **Alejandro** (@Alejandro-murillo — seguridad/Core OS; **temporalmente ausente**; conserva VPN/LUKS-TPM/air-gapped). Mateo fuera.
- **Deadline: 3 meses duros, sin holgura.** Doc a instructores 1 semana antes → sin renegociar criterios.
- **Repo:** `teamlocknet/nimbo` público, `main` protegida (check `estructura` required, sano).
- **`main` contiene:** cimientos + ISO mínima (1A) + CI compila (1B) + reproducibilidad completa 4 capas (1C) + CLI init/capture/report (2A-2C). Falta mergear: Xfce4 (3A, #17) y este maestro.
- **Reproducibilidad:** 🏁 COMPLETA y **reforzada** (bug latente `archive_trace` cerrado). Aguanta con Xfce dentro. ADRs 000–004.
- **CLI:** init+capture+report, integridad verificable (OK/MODIFICADO/AUSENTE).
- **Core OS:** escritorio Xfce4 mínimo, autologin, **368 MiB idle** (< 500 MB).
- Método: por secciones → nueva versión del maestro. **Briefs = handoffs; prompts = ciclo con Claude Code.** Ritmo iterativo. **Regla de stacks: no apilar PRs sin mergear.**
- **Codename `nimbo`** (desechable, un slug).

**Lo inmediato:**
1. **Alejandro (cuando vuelva) mergea el PR #17** y este maestro. No urgente (3A ya cerrado).
2. **Siguiente paso: 3B — hardening de seguridad del base** (terreno de Juan José). Revisar de paso la política del autologin.
3. **Después:** integrar CLI a la ISO + `.deb`; navegadores+Tor; resto de Vía B.
4. **Con reloj:** Design Partner (D2), D9 (trixie vs bookworm).

**Los 3 jefes de nivel (§10):** reproducibilidad (✅ COMPLETA y reforzada) · Design Partner (🔴 abierto) · LUKS + TPM 2.0 (pendiente, Vía B).

---

## 1. Identidad del proyecto

| | |
|---|---|
| **LockNet** | El grupo/colectivo (org GitHub `teamlocknet`). Autor y destinatario de la credibilidad pública. |
| **⟨producto — NOMBRE POR DEFINIR⟩** | El SO que se entrega. **Decisión abierta.** Candidatos heredados: *VELDORA* / *NEXUS Security OS*. |
| **`nimbo`** | **Codename interno desechable** + slug canónico. |

**Convención de nombre:** un **único slug `nimbo`** en TODO → el nombre real entra con **un find-and-replace global**. **Naming heredado a unificar** al decidir el nombre. Contexto: proyecto de grado SENA (ADSO); criterios de éxito en Acta §13.

## 2. El producto en una frase

*"Un sistema operativo de auditoría basado en Debian Stable que un equipo de ciberseguridad instala y usa el mismo día — navegación endurecida, red privada del propio equipo y trazabilidad de auditorías con evidencia verificable por hash — todo offline, reproducible bit a bit y sin una sola línea de telemetría."*

## 3. Alcance — qué es y qué NO es

**SÍ (todos, v1.0):** Core OS endurecido (ISO live+instalable, Debian+Xfce4, <500 MB idle) · navegación segura (endurecido tipo LibreWolf + puente Tor con detección de fugas) · red aislada (VPN P2P WireGuard/Tailscale bajo demanda) · CLI de auditoría (`init`/`capture`/`report`) · seguridad transversal (reproducibilidad bit a bit, LUKS+TPM 2.0, air-gapped con GPG) · distribución (CI/CD, repo APT propio, releases firmados, ADRs).

**NO:** kernel propio, 32 bits, infra de pago, y — deliberadamente — **cualquier IA dentro del producto.**

**⚠️ Doble plano de la IA:** el **producto** no lleva IA (diseño); el **desarrollo** sí la usa. No es contradicción — decirlo explícito en la sustentación.

## 4. Arquitectura de software

3 capas (DAS v2.0): **Capa 1** Debian Stable + systemd · **Capa 2** Xfce4 optimizado (✅ mínimo, 368 MiB) · **Capa 3** scripts Python 3 (CLI ✅ + `nimbo-net` pendiente). **CLI:** Command + Repository + servicios (hashing streaming, render determinista), inyección de dependencias. Estructura §4.1–4.3 de v1.1, en `main`.

**Build/reproducibilidad (COMPLETO y reforzado):** live-build en contenedor `debian:bookworm-slim` (por digest), `build-in-container.sh` paridad dev/CI, cadena de 4 capas ancladas, `snapshot.env` fuente única, compuerta `repro-verify.yml`. Controles: sortfile completo, squashfs `-processors 1`, caché APT off, `SOURCE_DATE_EPOCH`, anclaje snapshot, **+ normalización de `.disk/archive_trace`** (fix 3A). Escritorio Xfce4 vía `config/package-lists/desktop.list.chroot` (lista curada). Medición de RAM host-side (`measure-ram-in-qemu.sh`), no horneada en la ISO.

## 5. Los módulos — mapa de trabajo, dueños y palanca de IA

| Módulo | Dueño | Palanca de IA | Riesgo | Estado |
|---|---|---|---|---|
| ISO live-build + **Xfce4 endurecido** | Juan José (era Alejandro, D13) | Media | Medio | **ISO + Xfce4 mínimo ✅ (368 MiB); falta hardening (3B)** |
| CI/CD + repo APT + releases firmados | Juan José | Alta | Medio | CI + compuerta repro ✅; falta APT/releases |
| **Reproducibilidad bit a bit** | **Juan José** | **Baja** | **Muy alto** | **🏁 COMPLETA y reforzada** |
| **CLI de auditoría** | **Juan José** | **Muy alta** | Bajo | ✅ init+capture+report; falta RF-02 (2B.2), verify, empaquetado |
| Hardening + navegadores + Tor | **Juan José (hardening, D13)** / Alejandro (navegadores) | Media-alta | Medio | Hardening = 3B (siguiente); navegadores pendientes |
| VPN P2P + `nimbo-net join` | Alejandro | Alta | Bajo | Pendiente (Vía B, espera a Alejandro) |
| LUKS + TPM 2.0 (swtpm) | Alejandro | Media | Medio-alto | Pendiente (Vía B, espera a Alejandro) |
| Air-gapped (`nimbo-update-offline`) | Alejandro | Media-alta | Bajo | Pendiente (Vía B, espera a Alejandro) |
| QA / benchmarks RAM / smoke tests | Compartido (CI) | Alta | Medio | RAM idle medida ✅; 50 tests CLI ✅ |
| Docs, ADRs, documento maestro | Compartido + orquestador | Muy alta | Bajo | Al día (v1.9); ADR-000..004 |

## 6. Stack

Debian Stable + **live-build** (contenedor, toolchain anclada) · **Xfce4** (mínimo, lightdm) · **Python 3 / Typer** (target 3.11) · **pytest** · **pandoc** (opcional PDF) · **GitHub Actions** + **Pages** · **aptly** · **WireGuard** vía **Tailscale** (o Headscale) · **Calamares** · **LUKS + systemd-cryptenroll + TPM 2.0** (**swtpm**) · **QEMU/KVM** · **GPG** · **diffoscope** · **snapshot.debian.org** · **podman/docker** · **Git**. Todo FOSS, infra **$0**.

## 7. Método de trabajo

- **Roles:** **chat ORQUESTA** (piensa, escribe prompts maestros, revisa, mantiene este doc; no escribe código del producto) · **Claude Code programa** · **el equipo ejecuta, decide, verifica con los ojos** y hace lo del mundo físico (permisos, repo, sudo, hardware/TPM, merges/protección de rama, Design Partner).
- **Briefs vs prompts:** briefs = handoffs entre compañeros; Claude Code se dirige por prompts (prompt maestro → PLAN → revisión → aprobación). Se **detiene en bloqueadores y corrige premisas falsas** antes de tocar (validado; en 3A diagnosticó por inspección del chroot en vez de adivinar, y no forzó el fix de repro).
- **REGLA DE STACKS:** no apilar PRs sin mergear; nacen de `main`, se mergean secuenciales. Check *required* colgado → "¿es mergeable?", no "¿está mal el workflow?".
- **PRs pequeños y enfocados** (uno hace una cosa).
- **Ritmo iterativo:** un PR por vuelta; con pocos tokens se actualiza el maestro antes de cortar. **Tareas pesadas (builds de ISO, posible diagnóstico) se arrancan con ventana de tokens llena**, no al 35% — se prepara el prompt y se ejecuta con margen (aprendido en 3A).
- **Contrato anti-choque:** consumo por referencia. CODEOWNERS + `main` protegida + ramas `iniciales/tema`. *(Con Alejandro ausente y Juan José solo en `iso/`, el riesgo de choque es nulo por ahora.)*
- **Reproducibilidad desde el día 1** · **ritual de cierre** (CI verde + verificación con los ojos + commit + push + release firmado en hitos) · **corrección** (test rojo primero) · **checkpoint en el núcleo** (esquema/pipeline/PCR/hardening/receta/CI → parar y preguntar) · **no modelar sobre resúmenes** (diffoscope, no adivinar) · **verificar con los ojos** · **no decidir seguridad cansado** · **coherencia semántica de flags.**

### Principios no negociables
1. **REPRODUCIBILIDAD VERIFICABLE.** 2. **HERMETISMO.** 3. **COSTO CERO / TODO FOSS AUDITABLE.** 4. **EVIDENCIA CON HASH.** 5. **EL DETERMINISMO PRIMERO.** 6. **VERIFICAR CON LOS OJOS.** 7. **CHECKPOINT EN EL NÚCLEO.**

## 8. Plan de fases (13 semanas — guía)

| Sem | Sección / Foco | Entregable "verde" | Estado |
|---|---|---|---|
| 1 | Columna del build: 1A ISO · 1B CI · 1C reproducibilidad | ISO + CI + MATCH | 🏁 completo (y reforzado en 3A) |
| 2 | CLI `init` + logging | `init` | 🟢 `init` ✅; logging RF-02 → 2B.2 pendiente |
| 3 | CLI `capture` + **hardening base Xfce4 (<500 MB)** | Evidencia + RAM | 🟢 `capture` ✅; **Xfce4 ✅ 368 MiB (3A)**; hardening = 3B siguiente |
| 4 | CLI `report` (MD→PDF) + Calamares | CLI completo + ISO instalable | 🟢 `report` ✅; Calamares pendiente |
| 5 | Navegador endurecido + Tor + detección de fugas | Navegación | ⬜ |
| 6 | VPN P2P + `nimbo-net join` + docs local | CU-04 y RF-07 | ⬜ (espera a Alejandro) |
| 7 | Air-gapped (`nimbo-update-offline` + GPG) | RF-CORE-06 | ⬜ (espera a Alejandro) |
| 8 | LUKS+TPM en QEMU+swtpm + flujo passphrase | RF-CORE-05 en QEMU | ⬜ (espera a Alejandro) |
| 9 | Reproducibilidad bit-idéntica entre 2 runners | RNF-SEC-07 | 🏁 hecho (adelantado, reforzado) |
| 10 | Repo APT (aptly+Pages) + releases firmados | Distribución + release 1 | ⬜ (incluye empaquetar CLI a .deb) |
| 11 | QA + benchmarks + **auditoría Design Partner** | Hallazgos | ⬜ |
| 12 | ≥70% hallazgos + validación hardware real (TPM) + release final | ISO v1.0 firmada | ⬜ |
| 13 | Docs finales + ensayo de sustentación | Sustentación lista | ⬜ |

**Nota de secuencia:** Vía A hizo build (1A-1C) + CLI (2A-2C) + ahora el escritorio del Core OS (3A). Sigue 3B (hardening). La Vía B pura de Alejandro (VPN/LUKS-TPM/air-gapped) espera su regreso; lo urgente de su bloque (Core OS) ya arrancó por D13.

## 9. Registro de ejecución

**Fase 0 (✅):** v1.0 → v1.1. **Fase 1 — Paso 0 (✅ #1) · 1A (✅ #2) · 1B (✅ #3).**

**Fase 1 — 1C Reproducibilidad (🏁 COMPLETO, en `main`):** 1C.1 (#5) · 1C.2 ADR-001 (#6) · 1C.3 ADR-002/003 → MATCH (#8) · 1C.4 compuerta boot_id (#10) · 1C.5 snapshot/ADR-004 (#11) · 1C.6 toolchain/4 capas (#12). Maestro v1.6 (#13). Investigación `ci.yml` cerrada sin cambios.

**Fase 1 — CLI (✅):** 2A `init` (#14, main) · 2B `capture` (#15, main) · 2C `report` (#16, esperando merge — integridad OK/MODIFICADO/AUSENTE, 50 tests).

**Fase 1 — Core OS 3A: Xfce4 mínimo + RAM (✅ COMPLETO, PR #17, esperando merge):**
- Escritorio Xfce4 mínimo por lista curada (núcleo Xfce + drivers X explícitos + lightdm + `user-setup`/`sudo` + fuente base), sin metapaquetes. Autologin de sesión live vía drop-in `[Seat:*]` (revisar política en 3B). Arnés `measure-ram-in-qemu.sh` (host-side, no horneado).
- **RAM idle: 368 MiB** (< 500 MB, holgado). Autologin OK (screenshot). **repro-verify verde, MATCH `2fa70f02…`, runners distintos.**
- **Bug latente cerrado:** `.disk/archive_trace` (traza de mirror intermitente) causaba fallo de repro desde 1A, no era el payload de Xfce (bit-idéntico por diffoscope). Cerrado con hook de normalización.
- Aprendizaje: `user-setup`/`sudo` faltaban por `recommends=false` → sin usuario `nimbo` → login/autologin rotos; fix por declaración explícita.

**Estado de git:** `main` = Paso 0 + 1A + 1B + 1C + maestro v1.6 + CLI init/capture. Esperando merge de Alejandro: **#16 (report)** y **#17 (Xfce4)**. Maestro v1.9 por subir. Sin ramas de trabajo activas.

## 10. Los 3 jefes de nivel + palanca de IA

**Palanca:** la IA colapsa "código que escribimos"; en "sistemas que hay que observar" (reproducibilidad, ISO, RAM) el 24/7 + las máquinas potentes son la palanca. En 3A ambas cosas: la IA escribió la receta, la máquina midió y verificó.

1. **Reproducibilidad bit a bit — 🏁 COMPLETA y REFORZADA** (bit-idéntica + tercero + temporal + 4 capas + bug latente `archive_trace` cerrado). Aguanta con Xfce dentro.
2. **Design Partner (D2)** — riesgo logístico puro; **sigue sin cerrar.**
3. **LUKS + TPM 2.0** — pendiente, es de la Vía B (espera a Alejandro o eventual nuevo traslado). swtpm cubre QEMU; PCR se rompe con updates de kernel.

## 11. Recursos y costo cero

Escaso: tiempo y expertise, no dinero. Infra $0. **RAM del producto: 368 MiB idle con escritorio — muy holgado vs los 500 MB.** Pendiente no monetario futuro: **máquina con TPM 2.0 real** (semana 12). Riesgo de recursos operativo: `snapshot.debian.org` intermitente (mitigado con Retries + fix de `archive_trace`).

## 12. Decisiones abiertas y pendientes

| # | Ítem | Estado |
|---|---|---|
| D1 | **Nombre real del proyecto** | 🔴 Abierto (codename `nimbo`) |
| D2 | **Cerrar Design Partner** (o plan B) | 🔴 **Sigue abierto** |
| D3 | Reconciliar cronograma | ✅ 3 meses duros |
| D4 | Actualizar docs SENA a 2 personas | 🟠 Antes de la entrega final |
| D5 | Renegociar criterio de reproducibilidad | ⚫ Cerrada: no se renegocia |
| D6 | Owner de Python del CLI | ✅ Juan José |
| D7 | Codename provisional | ✅ `nimbo` |
| D8 | Vía inicial de Juan José | ✅ Build → CLI → Core OS |
| D9 | Debian Stable final (trixie vs bookworm) | 🟠 Abierto — anclado a bookworm |
| D10 | Frente tras reproducibilidad | ✅ CLI (hecho) → Core OS (en curso) |
| D11 | RF-02 dentro de 2B o 2B.2 | ✅ Separado a 2B.2 (pendiente de hacer) |
| D12 | `verify` como subcomando propio | 🟠 Deuda anotada |
| **D13** | **Traslado del Core OS endurecido (hardening+Xfce4) a Juan José por ausencia de Alejandro** | ✅ **Aplicado.** Alejandro conserva VPN/LUKS-TPM/air-gapped; revisar al volver |
| **D14** | **Política del autologin de la sesión live (¿aceptable en un SO de seguridad?)** | 🟠 A decidir en 3B |

## 13. Riesgos y deuda

- **Cronograma:** 13 semanas duras; cero margen. *Mitigantes:* los dos pilares grandes (reproducibilidad + CLI) hechos, y el Core OS ya arrancó pese a la ausencia de Alejandro (D13).
- **Concentración en una persona (agravado):** con Alejandro ausente, **todo lo activo es de Juan José**. Es el mayor riesgo de cronograma. Mitigación: Juan José asumió lo más urgente (Core OS); el resto de la Vía B (VPN/LUKS-TPM/air-gapped) queda en pausa hasta que Alejandro vuelva o se decida otro traslado.
- **Técnico:** reproducibilidad 🏁 hecha y reforzada; TPM/PCR (medio-alto, pendiente); RAM holgada (368 MiB, subirá algo con hardening/CLI integrados pero hay colchón).
- **Logístico:** Design Partner sin cerrar (alto).
- **Seguridad:** autologin de la sesión live a revisar en 3B (D14) — cómodo pero cuestionable en un SO de seguridad.
- **Deuda menor:** RF-02 (2B.2) · `verify` (D12) · empaquetar CLI a `.deb` + integrar a ISO · navegadores+Tor · warning Node 20 en actions.

---

*v1.9 — Hoy la casa por fin tiene luz y muebles. Después de meses de tuberías y cimientos invisibles, la ISO ya no arranca a una pantalla negra pidiendo usuario: abre a un escritorio, solo, y lo hace pesando trescientos sesenta y ocho megas cuando el techo eran quinientos —entramos holgados en la métrica que más miedo nos daba—. Y hubo un regalo escondido: al meter el escritorio, el guardián de la reproducibilidad se puso en rojo, y en vez de maldecir descubrimos que llevaba un defecto durmiendo desde el primer día —una traza del espejo de paquetes que pasaba por pura suerte— y que tarde o temprano nos habría traicionado en el peor momento. Lo cazamos hoy, con el escritorio de testigo. Eso es lo que hace un buen arnés: convierte la mala suerte futura en un problema de hoy, cuando aún hay calma para resolverlo. También cambió algo humano: Alejandro tuvo que ausentarse, y en vez de detener la obra, Juan José tomó el pico de su compañero y siguió cavando —guardándole su parte, no quitándosela—. La casa avanza con una sola mano firme por ahora. Falta endurecer las puertas y las ventanas —ese es el siguiente paso—, meter adentro las herramientas que ya construimos, y esperar a que la segunda mano vuelva para la red y las cerraduras. Pero por primera vez, si alguien abriera esta ISO, vería algo que se parece a un hogar.*
