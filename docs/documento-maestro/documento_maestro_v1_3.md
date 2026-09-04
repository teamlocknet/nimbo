# ⟨NOMBRE POR DEFINIR · codename `nimbo`⟩ — Documento maestro del proyecto
## Ecosistema / sistema operativo de ciberseguridad basado en Debian

**Versión:** 1.3 (Fase 1: ✅ **PASO 0 + 1A + 1B CERRADOS — nació la columna del build.** Hay una ISO live mínima que arranca, compilada tanto en local como **en CI en la nube**. Siguiente: Paso 1C, reproducibilidad con diffoscope — el jefe de nivel.)
**Grupo:** LockNet · **Repo:** `github.com/teamlocknet/nimbo` (público) · **Contexto:** Proyecto de grado — SENA, ADSO
**Fecha:** Septiembre 2026
**Estado:** 🟢 **EN MARCHA.** 2 personas + IA · **13 semanas duras** (sep → dic 2026, sin holgura) · 24/7 · dev en máquinas potentes → target gama baja · alcance **COMPLETO**. Vía A (build) de Juan José avanzando fuerte; Vía B (Alejandro) aún sin arrancar (estaba ocupado).

**Cambios frente a v1.2:**
1. **Nota de versionado:** v1.2 (cierre del Paso 0) quedó en un *stash* sin subir al repo; **v1.3 la consolida** junto con 1A y 1B y es **la versión canónica a subir** (reemplaza al v1.1 que aún está en `main`). Nada se pierde.
2. **Paso 1A CERRADO** — **PR #2** mergeado: ISO live mínima booteable con live-build (Debian 12 bookworm), **260 MB**, verificada arrancando en QEMU hasta `nimbo-live login:`. Build en **contenedor Debian (podman rootful)** sobre host Fedora. Detalles y aprendizajes en §9.
3. **Paso 1B CERRADO** — **PR #3** mergeado: workflow de GitHub Actions que **compila la ISO en la nube** reutilizando el mismo build en contenedor (paridad dev/CI real vía `CONTAINER_ENGINE` agnóstico podman↔docker). ISO de CI = **mismo conteo de bytes** que la local (272 629 760); imagen base **anclada por digest** (adelanto de 1C); artifact descargable. §9.
4. **D8 resuelta:** Juan José arrancó por **el build** (no el CLI), atacando temprano el jefe de nivel.

**⚠️ Estado ahora mismo (dónde retomar):** La columna del build existe: `commit → CI → ISO que compila y valida → artifact`. **Siguiente: Paso 1C — reproducibilidad bit a bit** (segunda compilación comparada + `diffoscope`), usando como base el SHA-256 actual (§9). Es el **jefe de nivel #1**; se ataca con cabeza fresca. Sigue **sin cerrar el Design Partner (D2)** y la **renegociación del criterio de reproducibilidad (D5)** — ambas con reloj corriendo.

---

## 0. ⚠️ DÓNDE QUEDAMOS — LEER PRIMERO PARA RETOMAR

**Fase 1: Pasos 0, 1A y 1B cerrados y en `main`. Nació la columna del build.**

**Decidido y fijado:**
- Equipo: **Juan José** (@Duque-Londono — líder/DevOps + build + dueño del CLI) + **Alejandro** (@Alejandro-murillo — seguridad/Core OS). Mateo fuera.
- **Deadline: 3 meses duros, sin holgura.**
- **Repo:** `teamlocknet/nimbo` público, `main` protegida (PR + code owners + 1 review + check `estructura` + sin push directo/force).
- **Build:** live-build dentro de contenedor Debian bookworm; **paridad dev/CI** (podman local ↔ docker CI, mismo `build-in-container.sh`). ISO mínima = 260 MB, arranca a login.
- Método: por secciones → nueva versión del maestro. **Briefs = handoffs entre compañeros; prompts = ciclo con Claude Code.**
- **Codename `nimbo`** (desechable, un slug).

**Lo inmediato:**
1. **Paso 1C (Vía A, Juan José) — el jefe de nivel:** segunda compilación del mismo commit + `diffoscope` para comparar; cerrar los no-determinismos restantes (§10). Base: SHA-256 `21072ac2…37320`.
2. **Vía B (Alejandro), cuando se libere:** primer `.deb` de `nimbo-net` + inventario de hardening. *(Aún sin arrancar.)*
3. **Cerrar Design Partner (D2)** y **renegociar criterio de reproducibilidad (D5)** — mover en paralelo.

**Los 3 jefes de nivel (§10):** reproducibilidad bit a bit (**en curso ahora**) · Design Partner · LUKS + TPM 2.0.

---

## 1. Identidad del proyecto

| | |
|---|---|
| **LockNet** | El grupo/colectivo (org GitHub `teamlocknet`). Autor y destinatario de la credibilidad pública. |
| **⟨producto — NOMBRE POR DEFINIR⟩** | El SO que se entrega. **Decisión abierta.** Candidatos heredados: *VELDORA* / *NEXUS Security OS*. |
| **`nimbo`** | **Codename interno desechable** + slug canónico. |

**Convención de nombre:** un **único slug `nimbo`** en TODO → el nombre real entra con **un find-and-replace global**. **Naming heredado a unificar** (VELDORA/NEXUS mezclados en docs SENA) al decidir el nombre. Contexto: proyecto de grado SENA (ADSO), evaluado por el Comité de Instructores; criterios de éxito en Acta §13.

## 2. El producto en una frase

*"Un sistema operativo de auditoría basado en Debian Stable que un equipo de ciberseguridad instala y usa el mismo día — navegación endurecida, red privada del propio equipo y trazabilidad de auditorías con evidencia verificable por hash — todo offline, reproducible bit a bit y sin una sola línea de telemetría."*

## 3. Alcance — qué es y qué NO es

**SÍ (todos, v1.0):** Core OS endurecido (ISO live+instalable, Debian+Xfce4, <500 MB idle) · navegación segura (endurecido tipo LibreWolf + puente Tor con detección de fugas) · red aislada (VPN P2P WireGuard/Tailscale bajo demanda) · CLI de auditoría (`init`/`capture`/`report`) · seguridad transversal (reproducibilidad bit a bit, LUKS+TPM 2.0, air-gapped con GPG) · distribución (CI/CD, repo APT propio, releases firmados, ADRs).

**NO:** kernel propio, 32 bits, infra de pago, y — deliberadamente — **cualquier IA dentro del producto.**

**⚠️ Doble plano de la IA:** el **producto** no lleva IA (diseño); el **desarrollo** sí la usa. Construir *con* IA algo que *no contiene* IA no es contradicción — decirlo explícito en la sustentación.

## 4. Arquitectura de software

3 capas (DAS v2.0): **Capa 1** Debian Stable + systemd · **Capa 2** Xfce4 optimizado · **Capa 3** scripts Python 3 (CLI de auditoría + `nimbo-net`). **Patrones del CLI:** Command + Repository. Estructura del monorepo/CLI/engagement: §4.1–4.3 de v1.1, ya en `main`.

**Build (materializado en 1A/1B):** live-build corre **dentro** de un contenedor `debian:bookworm-slim` (anclado por digest), no en el host. Un solo script `build-in-container.sh` sirve local (podman rootful, Fedora) y CI (docker, ubuntu-latest) cambiando solo `CONTAINER_ENGINE`. Esto da **paridad dev/CI** y sienta la base de la reproducibilidad.

## 5. Los módulos — mapa de trabajo, dueños y palanca de IA

| Módulo | Dueño | Palanca de IA | Riesgo | Estado |
|---|---|---|---|---|
| ISO live-build + Xfce4 endurecido | Juan José | Media | Medio | ISO mínima ✅; falta Xfce4/hardening |
| CI/CD + repo APT + releases firmados | Juan José | Alta | Medio | CI compila ISO ✅; falta APT/releases |
| **Reproducibilidad bit a bit** | **Juan José** | **Baja** (empírico) | **Muy alto** | **En curso (1C)** |
| **CLI de auditoría** | **Juan José** | **Muy alta** | Bajo | Pendiente |
| Hardening + navegadores + Tor | Alejandro | Media-alta | Medio | Pendiente |
| VPN P2P + `nimbo-net join` | Alejandro | Alta | Bajo | Pendiente |
| LUKS + TPM 2.0 (swtpm) | Alejandro | Media | Medio-alto | Pendiente |
| Air-gapped (`nimbo-update-offline`) | Alejandro | Media-alta | Bajo | Pendiente |
| QA / benchmarks RAM / smoke tests | Compartido (CI) | Alta | Medio | Validación de ISO ✅ base |
| Docs, ADRs, documento maestro | Compartido + orquestador | Muy alta | Bajo | Al día (v1.3) |

## 6. Stack

Debian Stable + **live-build** (en contenedor) · Xfce4 · **Python 3 / Typer** · **GitHub Actions** + **Pages** · **aptly** · **WireGuard** vía **Tailscale** (o Headscale) · **Calamares** · **LUKS + systemd-cryptenroll + TPM 2.0** (**swtpm**) · **QEMU/KVM** headless · **GPG** · **diffoscope** · **podman/docker** · **Git**. Todo FOSS, infra **$0** (Actions gratis en repo público).

## 7. Método de trabajo

- **Roles:** **chat ORQUESTA** (piensa, escribe prompts maestros, revisa, mantiene este doc; no escribe código del producto) · **Claude Code programa** · **el equipo ejecuta, decide, verifica con los ojos** y hace lo del mundo físico (permisos, repo, **operaciones privilegiadas/sudo**, hardware/TPM, Design Partner).
- **Briefs vs prompts:** briefs = handoffs entre los dos compañeros; Claude Code se dirige por prompts (prompt maestro → PLAN → revisión → aprobación por prompt). Claude Code **se detiene en bloqueadores** sin inventar (validado en Pasos 0, 1A, 1B).
- **Contrato anti-choque:** cada componente consume el output del otro **por referencia**, nunca edita a través de fronteras. CODEOWNERS + `main` protegida + ramas `iniciales/tema` + PRs pequeños.
- **Reproducibilidad desde el día 1** · **ritual de cierre** (CI verde + verificación con los ojos + commit + push + release firmado en hitos) · **corrección** (test rojo primero) · **checkpoint en el núcleo** (esquema/pipeline/PCR/hardening → parar y preguntar) · **no modelar sobre resúmenes** · **"compiló" ≠ "es reproducible"; "corrió en QEMU" ≠ "descifra en hardware"** · **no decidir seguridad cansado.**

### Principios no negociables
1. **REPRODUCIBILIDAD VERIFICABLE.** 2. **HERMETISMO.** 3. **COSTO CERO / TODO FOSS AUDITABLE.** 4. **EVIDENCIA CON HASH.** 5. **EL DETERMINISMO PRIMERO.** 6. **VERIFICAR CON LOS OJOS.** 7. **CHECKPOINT EN EL NÚCLEO.**

## 8. Plan de fases (13 semanas — guía; el orden real de la Vía A va por la columna del build)

| Sem | Sección / Foco | Entregable "verde" | Estado |
|---|---|---|---|
| 1 | **Columna del build:** 1A ISO mínima booteable · 1B CI compila ISO · 1C reproducibilidad | ISO en `main` + CI + diff | 🟢 1A ✅ · 1B ✅ · **1C siguiente** |
| 2 | CLI `init` + logging | `init` + primer diff | ⬜ |
| 3 | CLI `capture` (SHA-256) + hardening base Xfce4 (<500 MB) | Evidencia + RAM medida | ⬜ |
| 4 | CLI `report` (MD→PDF) + Calamares | CLI completo + ISO instalable | ⬜ |
| 5 | Navegador endurecido + Tor + detección de fugas | Módulo de navegación | ⬜ |
| 6 | VPN P2P (Tailscale) + `nimbo-net join` + docs local | CU-04 y RF-07 | ⬜ (Vía B arranca antes, en paralelo) |
| 7 | Air-gapped (`nimbo-update-offline` + GPG) | RF-CORE-06 | ⬜ |
| 8 | LUKS+TPM en QEMU+swtpm + flujo passphrase | RF-CORE-05 en QEMU | ⬜ |
| 9 | Reproducibilidad bit-idéntica entre 2 runners | RNF-SEC-07 | 🟡 **adelantada a 1C** (de-risking) |
| 10 | Repo APT (aptly+Pages) + releases firmados + integración | Distribución + release 1 | ⬜ |
| 11 | QA + benchmarks + **auditoría Design Partner** | Hallazgos | ⬜ |
| 12 | ≥70% hallazgos + validación hardware real (TPM) + release final | ISO v1.0 firmada | ⬜ |
| 13 | Docs finales + ensayo de sustentación | Sustentación lista | ⬜ |

**Nota de secuencia:** Juan José ejecuta la **columna del build (1A→1B→1C) primero**, lo que **adelanta la reproducibilidad** (originalmente semana 9) y reduce el mayor riesgo con energía fresca. El CLI y lo demás vienen después. Vía B (Alejandro) corre en paralelo cuando se libere.

## 9. Registro de ejecución

**Fase 0 — Fundación (CERRADA ✅):** v1.0 (reestructura + método) → v1.1 (codename + modelado de estructura).

**Fase 1 — Paso 0: Cimientos (CERRADO ✅):** repo público creado; **PR #1** (estructura §4, CODEOWNERS, ADR-000 + plantilla, CI `estructura`, README, `.gitignore`) revisado por Alejandro y mergeado; `main` protegida.

**Fase 1 — Paso 1A: ISO live mínima booteable (CERRADO ✅):**
- **PR #2** `jj/iso-min-bootable` mergeado. live-build (Debian 12 bookworm), sin escritorio. **ISO 260 MB** (272 629 760 bytes), kernel 6.1.0-52. Verificada en QEMU headless hasta `nimbo-live login:` (evidencia = boot-serial.log; la VGA sale negra porque la consola va a serie).
- **Aprendizajes documentados (oro):** (1) build **rootful obligatorio** en Fedora — debootstrap necesita `mknod`, podman rootless falla → lo corre el humano con `sudo`; (2) **`--network=host`** para que el contenedor rootful resuelva los mirrors Debian; (3) el menú de isolinux esperaba una tecla → el script manda Enter por el monitor de QEMU.
- Higiene de reproducibilidad aplicada (SOURCE_DATE_EPOCH, TZ=UTC, LC_ALL=C.UTF-8, sin recommends). Debian 12 fijado como **decisión abierta** (one-liner; a ADR cuando se decida).

**Fase 1 — Paso 1B: CI compila la ISO (CERRADO ✅):**
- **PR #3** `jj/ci-build-iso` mergeado. Workflow `build-iso.yml` (ubuntu-latest), **run exitoso en 6m 8s**. Triggers: manual + push/PR a `main` filtrado a `iso/live-build/**`. Concurrency + timeout 40m + retention 7 días.
- **Paridad dev/CI real:** `build-in-container.sh` agnóstico de motor (`CONTAINER_ENGINE` podman↔docker); misma receta local y CI. Imagen base **anclada por digest** (`debian@sha256:88200866…`) — adelanto de 1C.
- ISO de CI: **mismo conteo de bytes** que la local (272 629 760) — buena señal de consistencia (no prueba de bit-idéntico). **SHA-256 base: `21072ac22b3f8265978d5d04034123fd3757cd0eb23f98bbf490f3893ae37320`**. Validación (`file` + `xorriso -toc` + sanity de tamaño) que revienta el job si falla. Artifact `nimbo-iso-872a4eb` descargable.
- Disco del runner: 86 GB libres, nunca fue riesgo (limpieza quedó como seguro barato).

**Estado de git:** `main` = Paso 0 + 1A + 1B. Sin ramas de trabajo abiertas (tras mergear #2 y #3). Próxima: `jj/repro-diffoscope` (1C).

## 10. Los 3 jefes de nivel + palanca de IA

**Palanca:** la IA colapsa "código que escribimos"; **casi no toca** "sistemas que hay que observar" (reproducibilidad, TPM en hardware). El 24/7 va a lo segundo; las máquinas potentes son la palanca ahí.

1. **Reproducibilidad bit a bit (RNF-SEC-07) — EN CURSO (1C).** Ya hecho: higiene determinista + imagen base por digest + paridad dev/CI + mismo conteo de bytes local/CI. **Falta (deudas de 1C):** segunda compilación + `diffoscope`; anclar versiones de paquetes a **snapshot.debian.org**; orden/metadatos de **squashfs**; determinismo de **compresión** (gzip/xz). **D5 prioritaria:** renegociar con instructores el criterio hacia "hashes coincidentes entre 2 corridas de CI + no-determinismos documentados", sin colchón para perfección research-grade.
2. **Design Partner (D2)** — riesgo logístico puro; **sigue sin cerrar**; atacar ya o plan B.
3. **LUKS + TPM 2.0** — swtpm cubre QEMU; PCR se rompe con updates de kernel. Meta: receta validada en QEMU+swtpm; hardware real como extra.

## 11. Recursos y costo cero

Escaso: tiempo y expertise, no dinero. Infra $0 (GitHub público + Actions + Pages, Tailscale free, FOSS). No monetario: build de ISO ~6–20 min (mitigado por máquinas potentes) + **una máquina con TPM 2.0 real** para la semana 12. Curva más pronunciada: live-build/empaquetado Debian (parcialmente domada ya en 1A/1B).

## 12. Decisiones abiertas y pendientes

| # | Ítem | Estado |
|---|---|---|
| D1 | **Nombre real del proyecto** | 🔴 Abierto (codename `nimbo` cubre el interín) |
| D2 | **Cerrar Design Partner** (o plan B) | 🔴 **Sigue abierto — reloj corriendo** |
| D3 | Reconciliar cronograma | ✅ 3 meses duros, sin holgura |
| D4 | Actualizar docs SENA a 2 personas | 🟠 Antes de la próxima entrega |
| D5 | Renegociar criterio de reproducibilidad | 🔴 **Prioritario** (entrando a 1C) |
| D6 | Owner de Python del CLI | ✅ Juan José |
| D7 | Codename provisional | ✅ `nimbo` |
| D8 | Por cuál vía arranca Juan José | ✅ **Build** (columna 1A→1B→1C) |
| D9 | Qué Debian Stable se envía finalmente | 🟠 bookworm fijado para el ladrillo; formalizar en ADR |

## 13. Riesgos y deuda

- **Cronograma:** 13 semanas duras; cero margen. *Mitigante nuevo:* adelantar la reproducibilidad (1C) baja el riesgo de la semana 9.
- **Técnico:** reproducibilidad bit-idéntica (alto, en ataque ahora), TPM/PCR (medio-alto), tamaño en gama baja (bajo — vamos en 260 MB, holgado).
- **Logístico:** Design Partner sin cerrar (alto).
- **Deuda menor (no urgente):** warning de deprecación de Node 20 en las actions (`checkout`/`upload-artifact`) — limpiar cuando salgan versiones nuevas.

---

*v1.3 — Hoy la casa arrancó su motor por primera vez, y lo hizo dos veces igual. En la máquina de Juan y después, sola, en la nube, la misma receta levantó un sistema que respira: doscientos sesenta megas de Debian que arrancan hasta pedir usuario, sin escritorio todavía, desnudos y honestos. Y las dos veces pesó exactamente lo mismo, byte por byte —no es aún la prueba que buscamos, pero es la primera vez que el eco suena idéntico al grito, y eso da esperanza para la semana que más tememos—. Aprendimos peleando: que sobre Fedora hay que encerrar a Debian en un contenedor para que trabaje; que sin abrirle la red no encuentra sus espejos; que un menú tonto esperaba una tecla que nadie pulsaba. Cosas pequeñas que ahora están escritas para no volver a tropezar con ellas. Elegimos, además, ir de frente al monstruo: en vez de dejar la reproducibilidad para diciembre, la trajimos a hoy, mientras hay fuerzas. Lo que viene —diffoscope, dos compilaciones puestas frente a frente— es el examen de verdad: descubrir en qué se diferencian dos discos que deberían ser gemelos, y borrar esas diferencias una por una. El motor arrancó. Ahora toca hacerlo predecible.*
