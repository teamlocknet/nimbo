# ⟨NOMBRE POR DEFINIR · codename `nimbo`⟩ — Documento maestro del proyecto
## Ecosistema / sistema operativo de ciberseguridad basado en Debian

**Versión:** 2.0 (Fase 1: reproducibilidad (1C) completa · CLI (2A-2C) completo · Core OS con escritorio Xfce4 (3A) · **el sistema base queda ENDURECIDO — hermetismo/telemetría off (RNF-01) demostrado con captura de tráfico, y autologin separado live/instalado (D14 resuelto) — Paso 3B.1**. El salto a 2.0 marca un hito: la ISO ya no solo arranca a un escritorio, sino que arranca **hermética**. Falta: hardening fino (3B.2: sysctl kernel/red + PAM/cuentas), integrar CLI/navegadores/VPN a la ISO, y el resto de la Vía B.)
**Grupo:** LockNet · **Repo:** `github.com/teamlocknet/nimbo` (público) · **Contexto:** Proyecto de grado — SENA, ADSO
**Fecha:** Septiembre 2026
**Estado:** 🟢 **EN MARCHA, con buen ritmo.** 2 personas + IA — **Alejandro temporalmente no disponible; su bloque más urgente (Core OS endurecido) lo asumió Juan José** (que también es experto en ciberseguridad). 13 semanas duras (sep → dic 2026, sin holgura) · 24/7 · dev en máquinas potentes → target gama baja · alcance **COMPLETO**.

**Cambios frente a v1.9:**
1. **Paso 3B.1 — Hardening del sistema base: hermetismo + reducción de superficie + autologin live-only (✅ COMPLETO, PR #19).** Dos vías, sin tocar sysctl fino ni PAM (eso es 3B.2). Las **cuatro** verificaciones con los ojos en verde (escritorio usable + hermetismo + RAM + MATCH).
2. **HERMETISMO (RNF-01) — la bandera del proyecto, ahora MEDIBLE.** Hook chroot determinista que **enmascara** `apt-daily.timer`/`apt-daily-upgrade.timer` + sus `.service` y escribe `APT::Periodic::Enable "0"` (cierra el auto-update de apt por **ambas** vías: timer systemd y `cron.daily/apt-compat`) — era el **único** canal de "phone home" en idle del base. Coherente con air-gapped (RF-CORE-06): las actualizaciones van por `nimbo-update-offline` + GPG, nunca en silencio.
3. **La telemetría "clásica" NUNCA entró — documentado con evidencia, no con fe.** La introspección del **chroot real (398 paquetes)** confirma que `--apt-recommends false` (desde 1A) ya dejó fuera `popularity-contest`, `reportbug`, `apport`/`whoopsie`, `systemd-timesyncd` (⇒ sin NTP saliente), `systemd-resolved` (⇒ sin DNS-fallback), `avahi`, `cups`, `exim4`, `openssh-server`, `NetworkManager`, `unattended-upgrades`. Los únicos sockets habilitados son `dbus`/`journald`/`udev` = **UNIX/netlink locales**: **cero listeners TCP/UDP** de fábrica. *Documentar que algo nunca entró vale más que fingir que se apagó.*
4. **Evidencia de hermetismo reproducible y defendible.** Nuevo arnés host-side `verify-hermetismo-in-qemu.sh`: red **cautiva** de QEMU (SLIRP, no toca Internet) + `filter-dump` captura **cada** paquete del guest; ventana idle **fija** (120 s); lee los listeners por serie (`ss` + `/proc/net`). Veredicto: **0** salientes sospechosas (DNS/NTP/HTTP-S/SYN) y **0** listeners de red expuestos. Mismo espíritu que `measure-ram`: nada horneado en la ISO.
5. **D14 RESUELTO — autologin live sí / instalado no.** El autologin dejó de ser un fichero horneado en `/etc/lightdm/` (se filtraba al sistema instalado vía squashfs). Ahora lo genera **solo en el arranque live** un **script live-config** (`0150-nimbo-autologin`): live-only por construcción (live-config no corre en el sistema instalado por Calamares) ⇒ nunca persiste a instalado (coherente RNF-02). Verificado que sigue arrancando al escritorio Xfce.
6. **Reducción de superficie con contención honesta.** Solo se quita `apt-daily*` (superficie **y** red). Se **conservan** `cron`/`fstrim`/`e2scrub` con justificación (locales, sin red, útiles en el instalado; su masking se difiere a Calamares). *No se quita por quitar.*

**⚠️ Estado ahora mismo (dónde retomar):**
- **En `main`:** cimientos + ISO (1A) + CI (1B) + reproducibilidad 4 capas (1C) + CLI init/capture/report (2A-2C) + **Xfce4/3A** (PR #17 ya mergeado) + maestro v1.9 (#18).
- **Merges pendientes:** **PR #19 (hardening 3B.1)** y **este maestro v2.0** (su propio PR). El PR #19 llega con las 4 verificaciones en verde y CI completa (repro MATCH incluido).
- **Siguiente frente natural: Paso 3B.2 — hardening FINO** (sysctl de kernel/red, política de cuentas/PAM más allá del autologin). Es terreno de experto de Juan José y el ladrillo que sigue sobre el base ya endurecido.
- **Otros frentes abiertos:** integrar el CLI a la ISO + empaquetarlo `.deb`; navegadores endurecidos + Tor; y el resto de la Vía B de Alejandro (VPN, LUKS+TPM, air-gapped) cuando vuelva.
- **Pendientes con reloj:** Design Partner (D2), decisión D9 (trixie vs bookworm).

---

## 0. ⚠️ DÓNDE QUEDAMOS — LEER PRIMERO PARA RETOMAR

**Fase 1: reproducibilidad (1C) completa · CLI (2A-2C) completo · Core OS con escritorio Xfce4 (3A) + base ENDURECIDO/hermético (3B.1) completo. Todo en `main` salvo #19 (3B.1) y este maestro. El bloque que era de Alejandro avanza por mano de Juan José (D13).**

**Decidido y fijado:**
- Equipo: **Juan José** (@Duque-Londono — build+repro+CLI, y ahora **Core OS endurecido** por traslado D13) + **Alejandro** (@Alejandro-murillo — seguridad/Core OS; **temporalmente ausente**; conserva VPN/LUKS-TPM/air-gapped). Mateo fuera.
- **Deadline: 3 meses duros, sin holgura.** Doc a instructores 1 semana antes → sin renegociar criterios.
- **Repo:** `teamlocknet/nimbo` público, `main` protegida (check `estructura` required, sano).
- **`main` contiene:** cimientos + ISO mínima (1A) + CI compila (1B) + reproducibilidad completa 4 capas (1C) + CLI init/capture/report (2A-2C) + escritorio Xfce4 (3A). Falta mergear: hardening base (3B.1, #19) y este maestro.
- **Reproducibilidad:** 🏁 COMPLETA y **reforzada** (bug latente `archive_trace` cerrado). Aguanta con Xfce y con el hardening 3B.1 dentro (MATCH verde re-verificado). ADRs 000–004.
- **CLI:** init+capture+report, integridad verificable (OK/MODIFICADO/AUSENTE).
- **Core OS:** escritorio Xfce4 mínimo, autologin **live-only** (D14), **378 MiB idle** (< 500 MB), y **hermético** (RNF-01 demostrado con pcap).
- Método: por secciones → nueva versión del maestro. **Briefs = handoffs; prompts = ciclo con Claude Code.** Ritmo iterativo. **Regla de stacks: no apilar PRs sin mergear.**
- **Codename `nimbo`** (desechable, un slug).

**Lo inmediato:**
1. **Mergear PR #19 (3B.1)** y este maestro v2.0 (cada uno su PR; verificación con los ojos hecha).
2. **Siguiente paso: 3B.2 — hardening fino del base** (sysctl kernel/red + PAM/cuentas). Terreno de Juan José.
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

> Desde 3B.1 esa última cláusula — *"sin una sola línea de telemetría"* — deja de ser aspiración y pasa a ser **verificable**: se demuestra con una captura de tráfico en idle (0 salientes no solicitadas) y con la ausencia documentada de todo canal de "phone home".

## 3. Alcance — qué es y qué NO es

**SÍ (todos, v1.0):** Core OS endurecido (ISO live+instalable, Debian+Xfce4, <500 MB idle) · navegación segura (endurecido tipo LibreWolf + puente Tor con detección de fugas) · red aislada (VPN P2P WireGuard/Tailscale bajo demanda) · CLI de auditoría (`init`/`capture`/`report`) · seguridad transversal (reproducibilidad bit a bit, LUKS+TPM 2.0, air-gapped con GPG) · distribución (CI/CD, repo APT propio, releases firmados, ADRs).

**NO:** kernel propio, 32 bits, infra de pago, y — deliberadamente — **cualquier IA dentro del producto.**

**⚠️ Doble plano de la IA:** el **producto** no lleva IA (diseño); el **desarrollo** sí la usa. No es contradicción — decirlo explícito en la sustentación.

## 4. Arquitectura de software

3 capas (DAS v2.0): **Capa 1** Debian Stable + systemd (**endurecido: hermetismo/apt-daily off, 3B.1**) · **Capa 2** Xfce4 optimizado (✅ mínimo, 378 MiB, autologin live-only) · **Capa 3** scripts Python 3 (CLI ✅ + `nimbo-net` pendiente). **CLI:** Command + Repository + servicios (hashing streaming, render determinista), inyección de dependencias. Estructura §4.1–4.3 de v1.1, en `main`.

**Build/reproducibilidad (COMPLETO y reforzado):** live-build en contenedor `debian:bookworm-slim` (por digest), `build-in-container.sh` paridad dev/CI, cadena de 4 capas ancladas, `snapshot.env` fuente única, compuerta `repro-verify.yml`. Controles: sortfile completo, squashfs `-processors 1`, caché APT off, `SOURCE_DATE_EPOCH`, anclaje snapshot, **+ normalización de `.disk/archive_trace`** (fix 3A). Escritorio Xfce4 vía `config/package-lists/desktop.list.chroot` (lista curada).

**Hardening del base (3B.1):** hook chroot `0100-nimbo-hermetismo.hook.chroot` (determinista, no rompe repro) enmascara `apt-daily*` + `APT::Periodic off`. Autologin vía script **live-config** `0150-nimbo-autologin` (live-only, D14). Arneses host-side (no horneados en la ISO): `measure-ram-in-qemu.sh` (RAM) y `verify-hermetismo-in-qemu.sh` (pcap con red cautiva + `ss` → veredicto de hermetismo).

## 5. Los módulos — mapa de trabajo, dueños y palanca de IA

| Módulo | Dueño | Palanca de IA | Riesgo | Estado |
|---|---|---|---|---|
| ISO live-build + **Xfce4 endurecido** | Juan José (era Alejandro, D13) | Media | Medio | **ISO + Xfce4 (378 MiB) + base hermético (3B.1) ✅; falta hardening fino (3B.2)** |
| CI/CD + repo APT + releases firmados | Juan José | Alta | Medio | CI + compuerta repro ✅; falta APT/releases |
| **Reproducibilidad bit a bit** | **Juan José** | **Baja** | **Muy alto** | **🏁 COMPLETA y reforzada** (aguanta con 3B.1 dentro) |
| **CLI de auditoría** | **Juan José** | **Muy alta** | Bajo | ✅ init+capture+report; falta RF-02 (2B.2), verify, empaquetado |
| Hardening + navegadores + Tor | **Juan José (hardening, D13)** / Alejandro (navegadores) | Media-alta | Medio | **Hermetismo base ✅ (3B.1)**; falta 3B.2 (sysctl/PAM); navegadores pendientes |
| VPN P2P + `nimbo-net join` | Alejandro | Alta | Bajo | Pendiente (Vía B, espera a Alejandro) |
| LUKS + TPM 2.0 (swtpm) | Alejandro | Media | Medio-alto | Pendiente (Vía B, espera a Alejandro) |
| Air-gapped (`nimbo-update-offline`) | Alejandro | Media-alta | Bajo | Pendiente (Vía B, espera a Alejandro) |
| QA / benchmarks RAM / smoke tests | Compartido (CI) | Alta | Medio | RAM idle medida ✅; hermetismo verificable ✅; 50 tests CLI ✅ |
| Docs, ADRs, documento maestro | Compartido + orquestador | Muy alta | Bajo | Al día (v2.0); ADR-000..004 |

## 6. Stack

Debian Stable + **live-build** (contenedor, toolchain anclada) · **Xfce4** (mínimo, lightdm) · **Python 3 / Typer** (target 3.11) · **pytest** · **pandoc** (opcional PDF) · **GitHub Actions** + **Pages** · **aptly** · **WireGuard** vía **Tailscale** (o Headscale) · **Calamares** · **LUKS + systemd-cryptenroll + TPM 2.0** (**swtpm**) · **QEMU/KVM** · **tcpdump/socat** (evidencia de hermetismo) · **GPG** · **diffoscope** · **snapshot.debian.org** · **podman/docker** · **Git**. Todo FOSS, infra **$0**.

## 7. Método de trabajo

- **Roles:** **chat ORQUESTA** (piensa, escribe prompts maestros, revisa, mantiene este doc; no escribe código del producto) · **Claude Code programa** · **el equipo ejecuta, decide, verifica con los ojos** y hace lo del mundo físico (permisos, repo, sudo, hardware/TPM, merges/protección de rama, Design Partner).
- **Briefs vs prompts:** briefs = handoffs entre compañeros; Claude Code se dirige por prompts (prompt maestro → PLAN → revisión → aprobación). Se **detiene en bloqueadores y corrige premisas falsas** antes de tocar (validado; en 3A/3B.1 diagnosticó por inspección del chroot en vez de adivinar, y no forzó fixes de repro).
- **REGLA DE STACKS:** no apilar PRs sin mergear; nacen de `main`, se mergean secuenciales. Check *required* colgado → "¿es mergeable?", no "¿está mal el workflow?".
- **PRs pequeños y enfocados** (uno hace una cosa).
- **Ritmo iterativo:** un PR por vuelta; con pocos tokens se actualiza el maestro antes de cortar. **Tareas pesadas (builds de ISO, posible diagnóstico) se arrancan con ventana de tokens llena.** Los builds de ISO **flaquean por `snapshot.debian.org`** (intermitente): un reintento suele bastar — no es la receta.
- **Contrato anti-choque:** consumo por referencia. CODEOWNERS + `main` protegida + ramas `iniciales/tema`. *(Con Alejandro ausente y Juan José solo en `iso/`, el riesgo de choque es nulo por ahora.)*
- **Reproducibilidad desde el día 1** · **ritual de cierre** (CI verde + verificación con los ojos + commit + push + release firmado en hitos) · **corrección** (test rojo primero — en 3B.1 el falso ❌ del arnés se reprodujo y corrigió antes de dar por bueno) · **checkpoint en el núcleo** (esquema/pipeline/PCR/hardening/receta/CI → parar y preguntar) · **no modelar sobre resúmenes** (diffoscope/introspección, no adivinar) · **verificar con los ojos** · **no decidir seguridad cansado** · **coherencia semántica de flags.**

### Principios no negociables
1. **REPRODUCIBILIDAD VERIFICABLE.** 2. **HERMETISMO.** 3. **COSTO CERO / TODO FOSS AUDITABLE.** 4. **EVIDENCIA CON HASH.** 5. **EL DETERMINISMO PRIMERO.** 6. **VERIFICAR CON LOS OJOS.** 7. **CHECKPOINT EN EL NÚCLEO.**

## 8. Plan de fases (13 semanas — guía)

| Sem | Sección / Foco | Entregable "verde" | Estado |
|---|---|---|---|
| 1 | Columna del build: 1A ISO · 1B CI · 1C reproducibilidad | ISO + CI + MATCH | 🏁 completo (y reforzado en 3A) |
| 2 | CLI `init` + logging | `init` | 🟢 `init` ✅; logging RF-02 → 2B.2 pendiente |
| 3 | CLI `capture` + **hardening base Xfce4 (<500 MB)** | Evidencia + RAM | 🟢 `capture` ✅; **Xfce4 ✅ 378 MiB (3A) + base hermético ✅ (3B.1)**; falta 3B.2 |
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

**Nota de secuencia:** Vía A hizo build (1A-1C) + CLI (2A-2C) + escritorio (3A) + **hermetismo base (3B.1)**. Sigue 3B.2 (hardening fino). La Vía B pura de Alejandro (VPN/LUKS-TPM/air-gapped) espera su regreso; lo urgente de su bloque (Core OS) ya arrancó por D13.

## 9. Registro de ejecución

**Fase 0 (✅):** v1.0 → v1.1. **Fase 1 — Paso 0 (✅ #1) · 1A (✅ #2) · 1B (✅ #3).**

**Fase 1 — 1C Reproducibilidad (🏁 COMPLETO, en `main`):** 1C.1 (#5) · 1C.2 ADR-001 (#6) · 1C.3 ADR-002/003 → MATCH (#8) · 1C.4 compuerta boot_id (#10) · 1C.5 snapshot/ADR-004 (#11) · 1C.6 toolchain/4 capas (#12). Maestro v1.6 (#13).

**Fase 1 — CLI (✅, en `main`):** 2A `init` (#14) · 2B `capture` (#15) · 2C `report` (#16 — integridad OK/MODIFICADO/AUSENTE, 50 tests).

**Fase 1 — Core OS 3A: Xfce4 mínimo + RAM (✅ COMPLETO, #17 en `main`):** escritorio Xfce4 por lista curada (núcleo Xfce + drivers X explícitos + lightdm + `user-setup`/`sudo` + fuente base), sin metapaquetes. RAM idle 368 MiB. Bug latente `.disk/archive_trace` cerrado (diffoscope: payload Xfce bit-idéntico; el culpable era la traza intermitente del mirror). Maestro v1.9 (#18).

**Fase 1 — Core OS 3B.1: Hardening del base — hermetismo + superficie + autologin live-only (✅ COMPLETO, PR #19):**
- **Hermetismo (RNF-01):** hook chroot enmascara `apt-daily.timer`/`apt-daily-upgrade.timer` + `.service` y escribe `APT::Periodic::Enable "0"` (cierra timer systemd **y** `cron.daily/apt-compat`). Introspección del chroot (398 paquetes): la telemetría clásica (popcon/reportbug/whoopsie/timesyncd/resolved/avahi/cups/…) **nunca entró** (recommends=false desde 1A); cero listeners TCP/UDP de fábrica.
- **Autologin live/instalado (D14 resuelto):** de fichero horneado → **script live-config** `0150-nimbo-autologin` (live-only por construcción; nunca persiste a instalado, coherente RNF-02).
- **Superficie:** solo `apt-daily*`; `cron`/`fstrim`/`e2scrub` conservados (locales, útiles en instalado; masking diferido a Calamares).
- **Evidencia (4 ojos, todas verdes):** (1) arranca a Xfce y usable (screenshot); (2) **hermetismo** — pcap con red cautiva 120 s idle: 0 salientes sospechosas + 0 listeners expuestos (`verify-hermetismo-in-qemu.sh`); (3) **RAM idle 378 MiB** < 500 MB; (4) **repro-verify MATCH** bit-idéntico entre 2 runners (re-verificado en el commit final; `build-iso` verde).
- **Aprendizaje/anécdota de arnés:** la primera corrida de hermetismo dio ❌ por dos **sobre-clasificaciones del propio arnés** (contaba su etiqueta `LISTEN` y el socket cliente-DHCP udp/68 de bring-up; el contador de phone-home ya era 0). Se corrigió el **arnés** —no el producto, no había nada que ocultar— con justificación (bring-up local = ARP/DHCP/MLD link-local). Test rojo → verde.
- **Build:** flaqueó una vez en bootstrap (local **y** CI, paquete distinto cada vez) por intermitencia de `snapshot.debian.org`; reintento lo resolvió. Refuerza el riesgo conocido, no la receta.

**Estado de git:** `main` = Paso 0 + 1A + 1B + 1C + CLI (init/capture/report) + Xfce4 (3A) + maestro v1.9. **Pendiente de merge: PR #19 (3B.1)** y **este maestro v2.0** (su propio PR). Rama de trabajo: `jj/iso-hardening-3b1`.

## 10. Los 3 jefes de nivel + palanca de IA

**Palanca:** la IA colapsa "código que escribimos"; en "sistemas que hay que observar" (reproducibilidad, ISO, RAM, **hermetismo**) el 24/7 + las máquinas potentes son la palanca. En 3A/3B.1: la IA escribió la receta y los arneses, la máquina midió, capturó tráfico y verificó.

1. **Reproducibilidad bit a bit — 🏁 COMPLETA y REFORZADA** (bit-idéntica + tercero + temporal + 4 capas + `archive_trace` cerrado). Aguanta con Xfce y con el hardening 3B.1 dentro.
2. **Design Partner (D2)** — riesgo logístico puro; **sigue sin cerrar.**
3. **LUKS + TPM 2.0** — pendiente, es de la Vía B (espera a Alejandro o eventual nuevo traslado). swtpm cubre QEMU; PCR se rompe con updates de kernel.

## 11. Recursos y costo cero

Escaso: tiempo y expertise, no dinero. Infra $0. **RAM del producto: 378 MiB idle con escritorio endurecido — holgado vs los 500 MB (~120 MB de colchón).** Pendiente no monetario futuro: **máquina con TPM 2.0 real** (semana 12). Riesgo de recursos operativo: `snapshot.debian.org` intermitente (mitigado con Retries + fix de `archive_trace`; se acepta el reintento de build como coste conocido).

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
| **D14** | **Política del autologin de la sesión live** | ✅ **RESUELTA (3B.1): LIVE sí (efímero, arranque rápido) / INSTALADO no (credenciales reales, RNF-02).** Separado por construcción con un script live-config; el autologin no persiste al sistema instalado |

## 13. Riesgos y deuda

- **Cronograma:** 13 semanas duras; cero margen. *Mitigantes:* los dos pilares grandes (reproducibilidad + CLI) hechos, el Core OS ya arrancó y **ya endurece** pese a la ausencia de Alejandro (D13).
- **Concentración en una persona (agravado):** con Alejandro ausente, **todo lo activo es de Juan José**. Es el mayor riesgo de cronograma. Mitigación: Juan José asumió lo más urgente (Core OS); el resto de la Vía B (VPN/LUKS-TPM/air-gapped) queda en pausa hasta que Alejandro vuelva o se decida otro traslado.
- **Técnico:** reproducibilidad 🏁 hecha y reforzada; TPM/PCR (medio-alto, pendiente); RAM holgada (378 MiB, subirá algo con hardening fino/CLI integrados pero hay colchón).
- **Logístico:** Design Partner sin cerrar (alto).
- **Seguridad:** autologin **resuelto** (D14, live-only). Queda 3B.2 (sysctl kernel/red + PAM/cuentas) como siguiente capa de endurecimiento. El hermetismo del base es ahora **verificable** (arnés reproducible) — activo defendible ante el comité.
- **Deuda menor:** RF-02 (2B.2) · `verify` (D12) · empaquetar CLI a `.deb` + integrar a ISO · navegadores+Tor · warning Node 20 en actions · re-medir hermetismo/RAM cuando se integren CLI y navegadores.

---

*v2.0 — Hoy la casa cerró sus puertas por dentro. La semana pasada celebrábamos que por fin tenía luz y muebles; hoy comprobamos, con un micrófono pegado a la puerta durante dos minutos de silencio, que nadie dentro está llamando a escondidas a la calle. No había fugas —y lo bonito es que gran parte del mérito no fue apagar nada, sino descubrir que nunca habíamos dejado entrar a esos inquilinos ruidosos: el que cuenta cuántos vivimos aquí, el que pregunta la hora a un reloj lejano, el que quiere actualizarlo todo a medianoche sin permiso. La única voz que salía era la del que pide la dirección al llegar, y esa se le permite. También aprendimos algo sobre la honestidad de los instrumentos: nuestro propio detector se asustó de su reflejo y gritó "¡intruso!" al ver su etiqueta y al cartero del DHCP; en vez de bajarle el volumen para que callara, le enseñamos a distinguir un vecino de un extraño —porque un arnés que miente en verde es peor que no tener ninguno—. Y separamos, por fin, la puerta de la casa de exhibición de la puerta de la casa donde se vive: la primera se abre sola para que la visita entre rápido; la segunda, cuando alguien la habite de verdad, pedirá llave. Falta afinar cerrojos y ventanas —el paso que viene—, pero la promesa que más nos costaba mirar a los ojos, esa de "ni una sola línea de telemetría", ya no es una intención escrita en un folleto: es una grabación que podemos poner sobre la mesa del comité y decir, sin bajar la voz, escúchenlo ustedes mismos.*
