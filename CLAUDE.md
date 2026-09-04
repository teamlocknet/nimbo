# CLAUDE.md — Guía de reenclaje para Claude Code

> Lee este archivo **primero** cada vez que entres al proyecto. Te reorienta en 2 minutos.
> La **fuente de verdad viva** es `docs/documento-maestro/documento_maestro_v1_1.md`;
> este archivo es el índice operativo. Si hay conflicto, gana el documento maestro.

---

## 1. Qué es este proyecto

**Sistema operativo de auditoría de ciberseguridad basado en Debian Stable.** Proyecto
de grado del grupo **LockNet** (SENA · ADSO). Un equipo de ciberseguridad lo instala y lo
usa el mismo día: navegación endurecida, red privada del propio equipo y trazabilidad de
auditorías con evidencia verificable por hash — **todo offline, reproducible bit a bit y
sin una sola línea de telemetría**.

- **Deadline: 3 meses duros** (sep → dic 2026), sin holgura. Diciembre es un muro.
- **Equipo: 2 personas + IA.** Alcance **completo** (todos los módulos).
- **Doble plano de la IA (dilo explícito):** el **producto NO lleva IA** (sin LLM, sin
  Ollama, sin asistentes). El **desarrollo SÍ** la usa (chat orquesta + Claude Code programa).
  Construir *con* IA un sistema que *no contiene* IA no es contradicción.

## 2. El codename `nimbo` — regla de oro

El **nombre real está SIN DECIDIR** (candidatos heredados: VELDORA / NEXUS). Se usa el
codename **desechable `nimbo`** como **slug canónico único** en TODO: repos, paquetes
`.deb`, comandos (`nimbo-audit`, `nimbo-net`, `nimbo-update-offline`), namespaces Python
(`nimbo_audit`), rutas.

**Por qué:** el día que se decida el nombre real se adopta con **un solo find-and-replace
global** (`nimbo` → nombre) + un commit. **No te encariñes con `nimbo`: es prestado.**
Nunca introduzcas un nombre alternativo — rompería la propiedad del reemplazo único.
Decisión registrada en `docs/adr/ADR-000-codename-y-nombre.md` (Aceptado).

## 3. Dónde vive todo (rutas locales)

| Cosa | Ruta |
|---|---|
| **Este repo (todo el trabajo)** | `/home/juan/Proyectos/nimbo_repo` |
| Documento maestro (fuente de verdad) | `docs/documento-maestro/documento_maestro_v1_1.md` |
| Decisiones de arquitectura | `docs/adr/` (empieza en `ADR-000`) |
| Remoto GitHub | `https://github.com/teamlocknet/nimbo.git` (repo **público**, org LockNet) |

> ⚠️ Ojo: la carpeta `/home/juan/Proyectos/EcosistemaCiberseguridad` fue solo el punto de
> partida (tiene el `documento_maestro` original). **El repo real es `nimbo_repo`.** No
> confundir.

## 4. Equipo, dueños y CODEOWNERS

| Persona | GitHub | Rol | Áreas |
|---|---|---|---|
| **Juan José** | `@Duque-Londono` | Líder / DevOps · dueño del CLI de auditoría | `iso/`, `repro/`, `apt-repo/`, `ci/`, `.github/`, `packages/nimbo-audit/` |
| **Alejandro** | `@Alejandro-murillo` | Seguridad / Core OS | `packages/nimbo-net/`, `security/` |
| Ambos | — | — | `docs/` |

El mapeo vive en `.github/CODEOWNERS`. (Mateo quedó fuera del equipo.)

## 5. Modelo de trabajo (roles — línea dura)

- **Claude (chat) = ORQUESTADOR:** piensa, diseña, verifica, arma prompts, revisa y
  **mantiene el documento maestro. NO escribe el código del producto.**
- **Claude Code (tú) = INGENIERO:** escribes **todo el código real**, con el repo a la vista.
- **El equipo humano:** ejecuta, decide, hace lo del mundo físico (hardware/TPM, gama baja,
  cuentas, Design Partner) y **verifica con los ojos**.

### Rituales obligatorios
1. **Plan antes de código.** Ante una tarea nueva, responde primero con el plan (lista de
   archivos, sin contenido) y espera el "OK".
2. **Checkpoint en el núcleo → PÁRATE Y PREGUNTA.** Si algo toca **pipeline/CI, seguridad,
   esquema del engagement, PCR/TPM, hardening**, o está ambiguo: no inventes, pregunta.
3. **Verificar con los ojos.** "Compiló" ≠ "es reproducible"; "corrió en QEMU" ≠ "descifra
   en hardware". El equipo confirma visualmente antes de dar por cerrado.
4. **Corrección dirigida por test:** primero un test en **rojo** que reproduce el bug, luego
   el arreglo.
5. **No decidir seguridad cansado. No modelar sobre resúmenes** — captura el estado real.
6. **Pregunta, no inventes** datos no especificados (usuarios de GitHub, licencia, etc.).

### Principios no negociables
1. Reproducibilidad verificable · 2. Hermetismo (cero telemetría) · 3. Costo cero / todo
FOSS auditable · 4. Evidencia con hash (nada se sobrescribe en silencio) · 5. El
determinismo primero · 6. Verificar con los ojos · 7. Checkpoint en el núcleo.

## 6. Estructura del monorepo

```
nimbo/
├── CLAUDE.md                # este archivo
├── README.md
├── .gitignore
├── docs/
│   ├── adr/                 # decisiones de arquitectura (ADR-000…) — dueño: compartido
│   ├── documento-maestro/   # fuente de verdad viva — dueño: orquestador
│   └── manuales/            # usuario + ingeniería — dueño: compartido
├── iso/                     # Core OS — dueño: Juan José
│   ├── live-build/          #   config/ auto/ hooks/ includes.chroot/
│   ├── xfce4/               #   personalización + hardening del escritorio
│   └── calamares/           #   receta del instalador (engancha LUKS/TPM)
├── packages/                # módulos Python → .deb
│   ├── nimbo-audit/         #   CLI de auditoría — dueño: Juan José
│   └── nimbo-net/           #   red / VPN P2P — dueño: Alejandro
├── security/                # dueño: Alejandro
│   ├── luks-tpm/            #   systemd-cryptenroll: receta + flujo passphrase
│   ├── air-gapped/          #   nimbo-update-offline + verificación GPG
│   └── hardening/           #   políticas navegador, sysctl, telemetría off
├── repro/                   # reproducibilidad: SOURCE_DATE_EPOCH, helpers diffoscope — dueño: Juan José
├── apt-repo/                # config aptly → GitHub Pages — dueño: Juan José
├── ci/                      # scripts/workflows reutilizables — dueño: Juan José
└── .github/
    ├── CODEOWNERS
    └── workflows/
        └── ci.yml           # job `estructura` (verifica que existan las carpetas)
```

**Arquitectura (DAS v2.0, 3 capas):** Capa 1 Debian Stable + systemd (endurecido) · Capa 2
Xfce4 optimizado (<500 MB idle) · Capa 3 scripts Python 3 desacoplados (si un script falla,
kernel/red/escritorio siguen). **CLI:** patrones **Command** (una clase por subcomando:
`init`/`capture`/`report`) + **Repository** (abstrae el FS; permite migrar JSON→SQLite sin
reescribir el reporte). Sin API externa: opera sobre el FS local.

**Engagement que produce `init`:** `/home/user/audits/<engagement>/` con `metadata.json`,
`evidencia/index.json` (ruta + SHA-256 + timestamp por archivo), `logs/`, `reportes/`, `notas/`.

## 7. Stack

Debian Stable + **live-build** · Xfce4 · **Python 3 / Typer** · **GitHub Actions** +
**Pages** · **aptly** · **WireGuard** vía **Tailscale** (o Headscale) · **Calamares** ·
**LUKS + systemd-cryptenroll + TPM 2.0** (**swtpm** en pruebas) · **QEMU/KVM** headless ·
**GPG** · **diffoscope** · **Git**. Todo FOSS, infra **$0**.

## 8. Convenciones de Git

- **Nunca trabajes directo en `main`.** Rama por tarea; nombres tipo `chore/…`, `feat/…`,
  `fix/…`. (`main` tendrá protección: PR + review de code owner + status check `estructura`.)
- **Commits pequeños y descriptivos**, uno por bloque lógico. Mensajes en español,
  imperativo, con prefijo (`chore:`, `docs:`, `ci:`, `feat:`, `fix:`).
- **Un solo PR por tarea/paso**, contra `main`. **No hagas merge tú** — el equipo revisa y
  mergea (verificación con los ojos).
- **Trailer de atribución** al final de cada commit (y `Claude-Session:` con la URL de la
  sesión en curso):
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  ```
- Descripciones de PR terminan con: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- `gh` está autenticado como `Duque-Londono` con permiso de escritura en el repo.

## 9. Estado actual y plan de fases

**Fase 1 — Vía A (build) de Juan José, en marcha. Maestro en v1.3.**
- ✅ **Paso 0 (Cimientos)** — estructura + gobernanza + CI `estructura`. En `main` (PR #1).
- ✅ **Paso 1A (ISO live mínima booteable)** — live-build en `iso/live-build/`, build en
  contenedor Debian bookworm; ISO ~260 MB verificada en QEMU hasta login. En `main` (PR #2).
- ✅ **Paso 1B (compilar la ISO en CI)** — workflow `build-iso` que reusa el mismo build en
  contenedor (paridad dev/CI, `CONTAINER_ENGINE` podman↔docker); valida, imprime SHA-256 y
  sube la ISO como artifact. Imagen base anclada por digest. En `main` (PR #3).
- ⏭️ **Siguiente — Paso 1C (reproducibilidad):** `diffoscope` + segunda compilación comparada,
  usando el SHA-256 de 1B como base. Es uno de los 3 jefes de nivel. Deuda ya anotada en
  `iso/live-build/README.md` (anclar `snapshot.debian.org`, squashfs, compresión).
- Vía B (Alejandro): primer `.deb` de `nimbo-net` + inventario de hardening, en paralelo.

**Plan de 13 semanas (cada fila se documenta al cerrar, subiendo versión del maestro):**

| Sem | Foco | Entregable "verde" |
|---|---|---|
| 1 | Fundación: repo (esqueleto), ADR-000, Design Partner, live-build que bootee en CI | ISO mínima + esqueleto CLI |
| 2 | CLI `init` + logging · reproducibilidad ya (`diffoscope`+`SOURCE_DATE_EPOCH`) | `init` + primer diff |
| 3 | CLI `capture` (SHA-256) + hardening base Xfce4 (<500 MB) | Evidencia + RAM medida |
| 4 | CLI `report` (MD→PDF) + Calamares | CLI completo + ISO instalable |
| 5 | Navegador endurecido + Tor + detección de fugas | Módulo de navegación |
| 6 | VPN P2P (Tailscale) + `nimbo-net join` | CU-04 / RF-07 |
| 7 | Air-gapped (`nimbo-update-offline` + GPG) | RF-CORE-06 |
| 8 | LUKS+TPM en QEMU+swtpm + flujo passphrase | RF-CORE-05 en QEMU |
| 9 | **Reproducibilidad bit-idéntica** entre 2 runners | RNF-SEC-07 |
| 10 | Repo APT (aptly+Pages) + releases firmados | Distribución + release 1 |
| 11 | QA + benchmarks + auditoría Design Partner | Hallazgos |
| 12 | ≥70% hallazgos + validación hardware real (TPM) + release final | ISO v1.0 firmada |
| 13 | Docs finales + ensayo de sustentación | Sustentación lista |

**Los 3 "jefes de nivel" (lo más duro, poca palanca de IA):**
1. **Reproducibilidad bit a bit** (RNF-SEC-07) — sin holgura; criterio realista = "hashes
   coincidentes entre 2 corridas de CI + no-determinismos documentados".
2. **Design Partner** — riesgo logístico; cerrar en 2 semanas o plan B.
3. **LUKS + TPM 2.0** — swtpm cubre QEMU; la política de PCR se rompe con updates de kernel.

## 10. Decisiones abiertas (no las cierres tú)

- **D1 — Nombre real del proyecto:** 🔴 abierto (codename `nimbo` cubre el interín).
- **D2 — Cerrar Design Partner** (o plan B): 🔴 semanas 1–2.
- **D5 — Renegociar criterio de reproducibilidad:** 🔴 prioritario (sin colchón).
- **D4 — Actualizar docs SENA a 2 personas:** 🟠 antes de la próxima entrega.
- (Resueltas: D3 cronograma = 3 meses duros · D6 owner CLI = Juan José · D7 codename = `nimbo`.)

## 11. Anti-desborde — qué NO hacer sin que te lo pidan

- No adelantes fases. Termina lo pedido y para; si ves algo "necesario de una vez",
  **anótalo y menciónalo**, pero no lo hagas.
- No toques **configuración de GitHub** (protección de ramas, permisos, colaboradores) ni
  crees repos en la org: **eso es gestión humana.**
- No añadas dependencias, frameworks ni herramientas sin acordarlo.
- No introduzcas IA dentro del producto (principio de diseño).
- No inventes datos faltantes (usuarios, licencia, nombres): pregunta.
