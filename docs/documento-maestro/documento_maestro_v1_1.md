# ⟨NOMBRE POR DEFINIR · codename `nimbo`⟩ — Documento maestro del proyecto
## Ecosistema / sistema operativo de ciberseguridad basado en Debian

**Versión:** 1.1 (Fase 0: 🟡 **FUNDACIÓN** — codename interno adoptado + **modelado de la estructura** del proyecto. Sigue sin haber código: esta versión fija el esqueleto sobre papel para que Claude Code lo implemente en la próxima sesión.)
**Grupo:** LockNet · **Contexto:** Proyecto de grado — SENA, Análisis y Desarrollo de Software (ADSO)
**Fecha:** Septiembre 2026
**Estado:** 🟡 **ARRANQUE.** 2 personas + IA · **13 semanas duras** (sep → dic 2026, sin holgura oficial) · 24/7 · dev en máquinas potentes → target gama baja · alcance **COMPLETO**. Estructura ya modelada; implementación pendiente.

**Cambios frente a v1.0:**
1. **Codename interno `nimbo` adoptado** — handle desechable, no es el nombre. Regla de oro: un solo slug canónico en todo → el nombre real se adopta con **un find-and-replace global** (§1).
2. **Modelado de la estructura** — esqueleto del monorepo, estructura interna del CLI de auditoría (patrones Command + Repository del DAS) y estructura del engagement (§4.1–4.3). Es diseño sobre papel; **nada implementado aún**.
3. **D3 resuelta:** el proyecto arrancó tarde. Los 3 meses son **deadline duro, sin ventana oficial más larga detrás.** Diciembre es un muro. Consecuencia: la renegociación del criterio de reproducibilidad (D5) sube a **prioritaria** — ya no hay semanas de colchón (§10, §12).
4. **D7 resuelta:** codename autorizado como handle interno.

**⚠️ Estado ahora mismo (dónde retomar):** Estructura modelada y documentada. **Todavía no hay repositorio ni código.** Lo siguiente, en la **sesión completa (tras el reinicio):** Claude Code implementa este esqueleto — Fase 1. Sigue abierta la decisión del **nombre real** (§1, §12) y el **cierre del Design Partner** (§12). En este documento el producto se nombra `nimbo` (handle) o de forma descriptiva.

---

## 0. ⚠️ DÓNDE QUEDAMOS — LEER PRIMERO PARA RETOMAR

**Fase 0 (fundación), casi lista. Todavía cero código.**

**Decidido y fijado:**
- Equipo: **Juan José** (líder/DevOps + **dueño del CLI de auditoría**) + **Alejandro** (seguridad/Core OS). Mateo fuera.
- **Deadline: 3 meses duros, sin holgura.** Diciembre es un muro.
- Método: por secciones; cada cierre → nueva versión de **este** documento (reenclaje IA + tracker equipo).
- Roles IA: **chat = orquestador (no escribe código del producto); Claude Code = ingeniero.** (§7)
- **Codename interno `nimbo`** (desechable; un solo slug → rename por find-and-replace).
- **Estructura modelada** (§4.1–4.3): monorepo, CLI, engagement.

**Lo inmediato (próxima sesión = implementación):**
1. **Fase 1 con Claude Code:** crear org/repo GitHub con el esqueleto de §4, ADR-000 (registra codename + criterio de nombre), y arrancar por **el CLI de auditoría** (corazón, lo más IA-acelerable) **o** por **live-build + CI que ya bootee y ya corra `diffoscope`**. A elegir al empezar.
2. **Cerrar Design Partner** (o plan B) — semanas 1–2.
3. **Renegociar el criterio de reproducibilidad** con instructores (ahora prioritario, sin colchón).

**Los 3 jefes de nivel (§10):** reproducibilidad bit a bit · Design Partner · LUKS + TPM 2.0.

---

## 1. Identidad del proyecto

| | |
|---|---|
| **LockNet** | El grupo/colectivo. Autor y destinatario de la credibilidad pública del proyecto. |
| **⟨producto — NOMBRE POR DEFINIR⟩** | El SO que se entrega. **Decisión abierta.** Candidatos heredados: *VELDORA* / *NEXUS Security OS*. No decidido. |
| **`nimbo`** | **Codename interno desechable.** No es el nombre; es un marcador para poder trabajar sin anclar nada. |

**Convención de nombre (la que vuelve inofensivo al codename):** un **único slug canónico `nimbo`** en TODO — repos, paquetes `.deb`, comando (`nimbo-audit`, `nimbo-net`, `nimbo-update-offline`), namespaces de Python (`nimbo_audit`). Cuando se decida el nombre real, se adopta con **un solo find-and-replace global** (`nimbo` → nombre) + un commit. Sin deuda, sin encariñarse.

**⚠️ Naming heredado a unificar:** la documentación SENA mezcla VELDORA/NEXUS y veldora-audit/nexus-audit. Se unifica todo al decidir el nombre y se registra en ADR-000.

**Contexto académico:** proyecto de grado SENA (ADSO). Evaluado por el Comité de Instructores. Criterios de éxito en el Acta §13.

## 2. El producto en una frase

*"Un sistema operativo de auditoría basado en Debian Stable que un equipo de ciberseguridad instala y usa el mismo día — navegación endurecida, red privada del propio equipo y trazabilidad de auditorías con evidencia verificable por hash — todo offline, reproducible bit a bit y sin una sola línea de telemetría."*

## 3. Alcance — qué es y qué NO es

**SÍ (todos los módulos, v1.0):** Core OS endurecido (ISO live+instalable, Debian+Xfce4, <500 MB idle) · navegación segura (endurecido tipo LibreWolf + puente Tor con detección de fugas) · red aislada (VPN P2P WireGuard/Tailscale bajo demanda) · CLI de auditoría (`init`/`capture`/`report`) · seguridad transversal (reproducibilidad bit a bit, LUKS+TPM 2.0, air-gapped con GPG) · distribución (CI/CD, repo APT propio, releases firmados, ADRs).

**NO:** kernel propio, 32 bits, infra de pago, y — deliberadamente — **cualquier IA dentro del producto** (sin LLM, sin Ollama, sin asistentes).

**⚠️ Doble plano de la IA (decirlo explícito en la sustentación):** el **producto** no lleva IA (diseño). El **desarrollo** sí la usa (Claude orquesta + Claude Code programa). Construir *con* IA un sistema que *no contiene* IA **no es contradicción**.

## 4. Arquitectura de software

3 capas (DAS v2.0): **Capa 1** Debian Stable + systemd (heredado y endurecido) · **Capa 2** Xfce4 optimizado · **Capa 3** scripts Python 3 desacoplados (CLI de auditoría + `nimbo-net`). Si un script falla, kernel/red/escritorio siguen. **Patrones del CLI:** Command (una clase por subcomando) + Repository (abstrae el FS; permite migrar JSON→SQLite sin reescribir el reporte). Sin API externa: opera sobre el FS local.

### 4.1 Modelado de la estructura — esqueleto del monorepo

```
nimbo/                       # repo raíz (slug canónico)
├── README.md
├── docs/
│   ├── adr/                 # ADR-000 = codename + criterio de nombre; ADRs siguientes
│   ├── documento-maestro/   # ESTE documento vivo, versionado
│   └── manuales/            # usuario + ingeniería
├── iso/                     # Core OS
│   ├── live-build/          # config/ auto/ hooks/ includes.chroot/
│   ├── xfce4/               # personalización + hardening del escritorio
│   └── calamares/           # receta del instalador (engancha LUKS/TPM)
├── packages/                # módulos Python → empaquetados a .deb
│   ├── nimbo-audit/         # CLI de auditoría  (dueño: Juan José)
│   └── nimbo-net/           # red / VPN P2P      (dueño: Alejandro)
├── security/
│   ├── luks-tpm/            # systemd-cryptenroll: receta + docs + flujo passphrase
│   ├── air-gapped/          # nimbo-update-offline + verificación GPG
│   └── hardening/           # políticas navegador, sysctl, telemetría off
├── repro/                   # reproducibilidad: SOURCE_DATE_EPOCH, helpers diffoscope
├── apt-repo/                # config aptly → publicado en GitHub Pages
├── ci/                      # scripts y workflows reutilizables
└── .github/workflows/       # Actions: build ISO · diffoscope · tests · release firmado
```

### 4.2 Estructura interna del CLI de auditoría (patrones Command + Repository)

```
packages/nimbo-audit/
├── pyproject.toml
├── src/nimbo_audit/
│   ├── cli.py               # app Typer; cablea subcomandos
│   ├── comandos/            # PATRÓN COMMAND — una clase modular por subcomando
│   │   ├── base.py          #   interfaz común de ejecución
│   │   ├── init.py          #   RF-01: crea engagement + metadata
│   │   ├── capture.py       #   RF-03: copia evidencia + SHA-256 + index
│   │   └── report.py        #   RF-04: consolida metadata+logs+evidencia → MD/PDF
│   ├── repositorio/         # PATRÓN REPOSITORY — abstrae el FS (JSON hoy, SQLite futuro)
│   │   ├── engagement_repo.py   # metadata.json
│   │   └── evidencia_repo.py    # evidencia/index.json (rutas + hashes + timestamps)
│   ├── modelos/             # dataclasses: Engagement, Evidencia, Sesion
│   ├── servicios/           # hashing SHA-256 · sesión (script/asciinema) · render MD→PDF
│   └── errores.py           # excepciones limpias; degradación graciosa (RNF-08, sin traceback)
└── tests/                   # disciplina: test rojo del bug primero
```

### 4.3 Estructura del engagement (lo que produce `init` — ERS RF-01 + Casos de Uso)

```
/home/user/audits/<engagement>/
├── metadata.json            # id · fecha/hora inicio · analista (usuario del sistema)
├── evidencia/
│   └── index.json           # por archivo: ruta + SHA-256 + timestamp
├── logs/                    # registro de sesión con marcas de tiempo inicio/fin
├── reportes/                # salida de `report`: <nombre>.md (+ .pdf opcional)
└── notas/
```

## 5. Los módulos — mapa de trabajo, dueños y palanca de IA

| Módulo | Dueño | Palanca de IA | Riesgo |
|---|---|---|---|
| ISO live-build + Xfce4 endurecido | Juan José | Media | Medio |
| CI/CD + repo APT + releases firmados | Juan José | Alta | Medio |
| **Reproducibilidad bit a bit** | **Juan José** | **Baja** (empírico) | **Muy alto** |
| **CLI de auditoría** | **Juan José** | **Muy alta** | Bajo |
| Hardening + navegadores + Tor | Alejandro | Media-alta | Medio |
| VPN P2P + `nimbo-net join` | Alejandro | Alta | Bajo |
| LUKS + TPM 2.0 (swtpm) | Alejandro | Media | Medio-alto |
| Air-gapped (`nimbo-update-offline`) | Alejandro | Media-alta | Bajo |
| QA / benchmarks RAM / smoke tests | Compartido (CI) | Alta | Medio |
| Docs, ADRs, documento maestro | Compartido + orquestador | Muy alta | Bajo |

## 6. Stack

Debian Stable + **live-build** · Xfce4 · **Python 3 / Typer** · **GitHub Actions** + **Pages** · **aptly** · **WireGuard** vía **Tailscale** (o Headscale) · **Calamares** · **LUKS + systemd-cryptenroll + TPM 2.0** (**swtpm** en pruebas) · **QEMU/KVM** headless · **GPG** · **diffoscope** · **Git**. Todo FOSS, infra **$0**.

## 7. Método de trabajo

- **Roles (línea dura):** **Claude (chat) ORQUESTA** — piensa, diseña, verifica, arma prompts, revisa y **mantiene este documento maestro; no escribe el código del producto.** **Todo el código del producto lo escribe Claude Code**, con el repo real a la vista. **El equipo ejecuta, decide, verifica con los ojos** y hace lo del mundo físico (hardware/TPM, gama baja, cuentas, Design Partner).
- **Por secciones:** al cerrar cada sección, **este documento sube de versión** (nuevo "dónde quedamos" + tabla de fases). Es el reenclaje de la IA y el tracker del equipo.
- **Reproducibilidad desde el día 1:** `diffoscope` + `SOURCE_DATE_EPOCH` en el primer build.
- **Ritual de cierre:** CI verde + `diffoscope` sin diferencias (o documentadas) + **verificación con los ojos** (bootea, RAM <500 MB, descifra, hashes coinciden) + commit + push + release firmado en hitos.
- **Corrección:** test en **rojo** que reproduce el bug primero, luego el arreglo.
- **Checkpoint en el núcleo:** tocar esquema del engagement / pipeline / PCR / hardening → **parar y preguntar.**
- **No modelar sobre resúmenes:** capturar el estado real antes del fix. **"Compiló" ≠ "es reproducible"; "corrió en QEMU" ≠ "descifra en hardware".**
- **No decidir seguridad cansado.**

### Principios no negociables
1. **REPRODUCIBILIDAD VERIFICABLE.** 2. **HERMETISMO** (cero telemetría). 3. **COSTO CERO / TODO FOSS AUDITABLE.** 4. **EVIDENCIA CON HASH** (nada se sobrescribe en silencio). 5. **EL DETERMINISMO PRIMERO.** 6. **VERIFICAR CON LOS OJOS.** 7. **CHECKPOINT EN EL NÚCLEO.**

## 8. Plan de fases (13 semanas — cada fila es una sección que se documenta al cerrar)

| Sem | Sección / Foco | Entregable "verde" | Estado |
|---|---|---|---|
| 1 | Fundación: org GitHub, repos (esqueleto §4), ADR-000, cerrar Design Partner, live-build que **ya bootee en CI** | ISO mínima + esqueleto CLI | 🟡 estructura modelada; falta implementar |
| 2 | CLI `init` + logging · **reproducibilidad ya** (`diffoscope`+`SOURCE_DATE_EPOCH`) | `init` + primer diff | ⬜ |
| 3 | CLI `capture` (SHA-256) + hardening base Xfce4 (<500 MB) | Evidencia + RAM medida | ⬜ |
| 4 | CLI `report` (MD→PDF) + Calamares | **CLI completo** + ISO instalable | ⬜ |
| 5 | Navegador endurecido + Tor + detección de fugas | Módulo de navegación | ⬜ |
| 6 | VPN P2P (Tailscale) + `nimbo-net join` + docs local | CU-04 y RF-07 | ⬜ |
| 7 | Air-gapped (`nimbo-update-offline` + GPG) | RF-CORE-06 | ⬜ |
| 8 | LUKS+TPM en QEMU+swtpm + flujo passphrase | RF-CORE-05 en QEMU | ⬜ |
| 9 | **Jefe: reproducibilidad bit-idéntica** entre 2 runners | RNF-SEC-07 | ⬜ |
| 10 | Repo APT (aptly+Pages) + releases firmados + integración | Distribución + release 1 | ⬜ |
| 11 | QA + benchmarks + **auditoría Design Partner** | Hallazgos | ⬜ |
| 12 | ≥70% hallazgos + validación hardware real (TPM) + release final | ISO v1.0 firmada | ⬜ |
| 13 | Docs finales + ensayo de sustentación | Sustentación lista | ⬜ |

## 9. Registro de ejecución

**Fase 0 — Fundación (EN CURSO 🟡):** v1.0 (reestructura + método) → v1.1 (**codename `nimbo`** + **modelado de estructura** §4.1–4.3 + D3/D7 resueltas). **Nada de código ni infraestructura aún.** Siguiente: Fase 1 — implementación del esqueleto por Claude Code.

## 10. Los 3 jefes de nivel + palanca de IA

**Palanca:** la IA colapsa "código que escribimos" (CLI, CI, wrappers, docs, tests); **casi no toca** "sistemas que hay que observar" (reproducibilidad, TPM en hardware, boot/tamaño). El 24/7 va a lo segundo; las máquinas potentes son la palanca ahí (más builds/día = más iteraciones de reproducibilidad).

1. **Reproducibilidad bit a bit (RNF-SEC-07)** — el más duro. **Sin holgura (D3), renegociar su criterio de éxito es ahora prioritario (D5):** apuntar a "hashes coincidentes entre 2 corridas de CI + no-determinismos documentados" en vez de perfección research-grade.
2. **Design Partner** — riesgo logístico puro; cerrar en 2 semanas o plan B.
3. **LUKS + TPM 2.0** — swtpm cubre QEMU; la política de PCR se rompe con updates de kernel. Meta firme: receta validada en QEMU+swtpm; hardware real como extra.

## 11. Recursos y costo cero

Escaso: tiempo y expertise, no dinero. Infra $0 (GitHub público + Actions + Pages, Tailscale free, stack FOSS). No monetario: build de ISO lento (mitigado por máquinas potentes) + **una máquina con TPM 2.0 real** para la semana 12. Curva más pronunciada: **live-build / empaquetado Debian.**

## 12. Decisiones abiertas y pendientes

| # | Ítem | Estado |
|---|---|---|
| D1 | **Nombre real del proyecto** | 🔴 Abierto (sin prisa; codename `nimbo` cubre el interín) |
| D2 | **Cerrar Design Partner** (o plan B) | 🔴 Semanas 1–2 |
| D3 | Reconciliar cronograma | ✅ **Resuelto: 3 meses duros, sin holgura. Dic = muro.** |
| D4 | Actualizar docs SENA a 2 personas | 🟠 Antes de la próxima entrega |
| D5 | Renegociar criterio de reproducibilidad | 🟠→🔴 **Prioritario** (sin colchón tras D3) |
| D6 | Owner de Python del CLI | ✅ **Juan José** |
| D7 | Codename provisional | ✅ **`nimbo`** (desechable, un-slug) |

## 13. Riesgos

- **Cronograma:** 13 semanas duras, 2 personas, alcance completo. Sin colchón (D3): cero margen en la semana 9.
- **Técnico:** reproducibilidad (alto), TPM/PCR (medio-alto), tamaño/boot en gama baja (medio).
- **Logístico:** Design Partner que no entregue (alto, plan B temprano).
- **Credibilidad:** naming inconsistente + docs que dicen 3 personas (barato de arreglar).
- **Expertise:** live-build/empaquetado Debian.

---

*v1.1 — Antes de poner un solo ladrillo, dibujamos los cuartos. Hoy el proyecto tiene forma aunque no tenga aún materia: un lugar para el código que lee la evidencia y le pone su huella, otro para la máquina que arma el disco, otro para las llaves que lo cifran, y un cuarto —el más importante— donde este documento se quedará a vivir y a crecer, versión tras versión, para que ninguna sesión empiece a ciegas. Le pusimos un nombre falso a la casa, `nimbo`, sabiendo que es prestado; un apodo de obra que se caerá solo el día que aparezca el nombre verdadero, y no dejará marca. Y aceptamos, sin adornos, la verdad del reloj: no hay seis meses ni cinco, hay tres, y empezaron tarde. Eso no achica el plano —lo hace más honesto—: cada cuarto que dibujamos hoy es un cuarto que Claude Code levantará mañana con las manos en el repo, mientras nosotros miramos que cada pared quede derecha. El plano está. Falta construir. Y el que construye descansa ahora para volver entero.*
