# CLAUDE.md — Guía de reenclaje para Claude Code

> Lee este archivo **primero** cada vez que entres al proyecto. Te reorienta en 2 minutos.
> La **fuente de verdad viva** es el maestro vivo, que está **FUERA del repo**:
> `~/Projects/EcosistemaCiberseguridad/OS_Ciberseguridad/documento_maestro_v2_4.md`
> (lo mantiene Juan José). El `documento_maestro_v2_0.md` de
> `docs/documento-maestro/` es histórico y está desactualizado: no usarlo como fuente.
> Este archivo es el índice operativo. Si hay conflicto, gana el maestro vivo.

---

## 1. Qué es este proyecto

**Sistema operativo de auditoría de ciberseguridad basado en Debian, rama con soporte LTS
(bookworm — [ADR-005](docs/adr/ADR-005-quedarse-en-bookworm-v1.md)).** Proyecto
de grado del grupo **LockNet** (SENA · ADSO). Un equipo de ciberseguridad lo instala y lo
usa el mismo día: navegación endurecida, red privada del propio equipo y trazabilidad de
auditorías con evidencia verificable por hash — **todo offline, reproducible bit a bit y
sin una sola línea de telemetría**.

- **Entrega: 30-nov-2026** (fecha de sustentación por confirmar, D16), sin holgura.
- **Equipo: 3 personas + IA** (reparto por módulos, D18). **Alcance por prioridad**
  (D15 = opción B, 9-nov): primero los requisitos de prioridad Alta; los de prioridad
  Media, si da el tiempo.
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
| **Este repo (todo el trabajo)** | `~/Projects/nimbo_repo` en la máquina de Juan José (cada cual tiene su clon; en Windows, dentro de WSL2, no en `/mnt/c`) |
| Documento maestro vivo (fuente de verdad, **fuera del repo**) | `~/Projects/EcosistemaCiberseguridad/OS_Ciberseguridad/documento_maestro_v2_4.md` |
| Plan de trabajo por persona (fuera del repo) | `plan_de_trabajo_equipo.md`, junto al maestro |
| Documento maestro histórico (desactualizado, no usar) | `docs/documento-maestro/documento_maestro_v2_0.md` |
| Decisiones de arquitectura | `docs/adr/` (plantilla: `docs/adr/_plantilla-adr.md`) |
| Hallazgos | `docs/hallazgos/` (H-001, H-004…) |
| Remoto GitHub | `https://github.com/teamlocknet/nimbo.git` (repo **público**, cuenta `teamlocknet`) |

## 4. Equipo, dueños y CODEOWNERS

Reparto vigente (D18, 28-oct; detalle en el maestro §1 y en el plan de trabajo):

| Persona | GitHub | Responsabilidades |
|---|---|---|
| **Juan José** | `@Duque-Londono` | Núcleo de la ISO (receta, reproducibilidad, hermetismo, instalador), LUKS + TPM (`nimbo-tpm-setup`), verificación en QEMU y hardware real, revisión y merge de todos los PR, checkpoints, custodia de las claves reales de firma, documento maestro |
| **Alejandro** | `@Alejandro-Murillo22` | CLI `nimbo-audit` (`.deb`, integración a la ISO, `verify`) · distribución (repo APT y releases firmados) · red privada del equipo (`nimbo-net`) |
| **Emmanuel** | `@Cardozo-Mosquera` | Navegación segura (navegador endurecido + Tor con detección de fugas) · air-gapped con GPG · hardening fino 3B.2 (sysctl/PAM) · documentación y material del Design Partner |
| Todos | — | `docs/` |

`.github/CODEOWNERS` sigue este reparto (10-nov): cada área tiene a su dueño **y** a Juan
José, y basta la aprobación de uno. `main` exige una aprobación y nadie puede aprobar su
propio PR. Cambiar `CODEOWNERS` toca `.github/` (núcleo): lo decide Juan José.

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
7. **Credenciales (regla permanente, 2026-10-23):**
   - **Nunca pidas contraseñas, passphrases ni claves** al equipo, ni de VMs "de prueba"
     (los discos de prueba suelen ser copias de instalaciones reales). Si una prueba
     necesita una credencial, diseña el camino para que la teclee la persona, o genera
     credenciales propias de la prueba.
   - **Ninguna credencial entra al repo, ni siquiera de prueba.** Si una evidencia la
     contiene (p. ej. la clave de recuperación de `systemd-cryptenroll`), se **redacta**
     antes de versionarla o de mostrarla en la sustentación; el original solo vive en
     ficheros ignorados por git.
   - Motivo: es un proyecto de ciberseguridad; ese atajo es justo lo que el producto
     existe para evitar.

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
│   ├── adr/                 # decisiones de arquitectura (ADR-000…020) — compartido
│   ├── documento-maestro/   # solo el v2.0 histórico (el vivo está fuera del repo)
│   ├── hallazgos/           # H-001, H-004… (material de sustentación)
│   └── manuales/            # usuario + ingeniería — compartido
├── iso/                     # Core OS — Juan José (núcleo: checkpoint)
│   ├── live-build/          #   config/ auto/ hooks/ includes.chroot/ + arnés QEMU
│   ├── branding/            #   SVG propio del instalador (CREDITOS.md)
│   ├── xfce4/               #   personalización + hardening del escritorio
│   └── calamares/           #   receta del instalador (engancha LUKS/TPM)
├── packages/                # módulos Python → .deb
│   ├── nimbo-audit/         #   CLI de auditoría — Alejandro (ADR-010)
│   ├── nimbo-nav/           #   navegación segura + modo Tor — Emmanuel (ADR-012)
│   ├── nimbo-net/           #   red privada del equipo (WireGuard) — Alejandro (ADR-011)
│   ├── nimbo-red/           #   red por cable a demanda — Juan José (ADR-019)
│   └── nimbo-update-offline/ #  actualización sin red con GPG — Emmanuel (ADR-013)
├── security/
│   ├── luks-tpm/            #   nimbo-tpm-setup + evidencias — Juan José
│   ├── air-gapped/          #   documentación air-gapped (el código: packages/nimbo-update-offline) — Emmanuel
│   └── hardening/           #   sysctl, PAM (3B.2) — Emmanuel (núcleo: checkpoint)
├── repro/                   # reproducibilidad: build-twice, diff-isos, espejo/ (ADR-016) — Juan José
├── apt-repo/                # config aptly → GitHub Pages — Alejandro
├── release/                 # release firmado: release.py, procedencia (ADR-015) — Alejandro + Juan José
├── ci/                      # scripts reutilizables — Juan José
└── .github/
    ├── CODEOWNERS
    └── workflows/
        ├── ci.yml           # jobs `estructura`, `tests-cli-bookworm`, `tests-modulos-bookworm` (×4),
        │                    #   `tests-release-bookworm`, `tests-build-scripts`
        ├── build-iso.yml    # compila la ISO en contenedor y la sube como artifact (caduca a los 7 días)
        ├── repro-verify.yml # compuerta MATCH ×2 (dos compilaciones, mismo SHA-256) + run semanal
        └── release.yml      # release firmado a mano (environment `release`, ADR-015)
```

**Arquitectura (DAS v2.0, 3 capas):** Capa 1 Debian bookworm (LTS) + systemd (endurecido) · Capa 2
Xfce4 optimizado (<500 MB idle) · Capa 3 scripts Python 3 desacoplados (si un script falla,
kernel/red/escritorio siguen). **CLI:** patrones **Command** (una clase por subcomando:
`init`/`capture`/`report`/`verify`) + **Repository** (abstrae el FS; permite migrar JSON→SQLite sin
reescribir el reporte). Sin API externa: opera sobre el FS local.

**Engagement que produce `init`:** `/home/user/audits/<engagement>/` con `metadata.json`,
`evidencia/index.json` (ruta + SHA-256 + timestamp por archivo), `logs/`, `reportes/`, `notas/`.

## 7. Stack

Debian bookworm (rama LTS, ADR-005) + **live-build** · Xfce4 · **Python 3 / Typer** · **GitHub Actions** +
**Pages** · **aptly** · **WireGuard** (RF-RED-01: `nimbo-net join`; Tailscale/Headscale se
evalúan en ADR-011, sin decidir) · **Calamares 3.3.8** (única excepción de backports) ·
**LUKS + systemd-cryptenroll + TPM 2.0** (**swtpm** en pruebas) · **QEMU/KVM** headless ·
**GPG** · **diffoscope** · **Git**. Todo FOSS, infra **$0**.

## 8. Convenciones de Git

- **Nunca trabajes directo en `main`.** Rama por tarea, desde `main` actualizado; PRs
  pequeños y no apilados. Ramas por persona: `jj/…`, `alejandro/…`, `emmanuel/…`
  (también se usan `chore/…`, `feat/…`, `fix/…`, `docs/…`). Nadie hace *force-push* a
  ramas ajenas. `main` está protegida: exige una aprobación de `CODEOWNERS` y nadie
  aprueba su propio PR.
- **Commits pequeños y descriptivos**, uno por bloque lógico. Mensajes en español,
  imperativo, con prefijo (`chore:`, `docs:`, `ci:`, `feat:`, `fix:`).
- **Un solo PR por tarea/paso**, contra `main`. **No hagas merge tú**: Juan José revisa y
  mergea (verificación con los ojos).
- **Trailer de atribución** al final de cada commit (y `Claude-Session:` con la URL de la
  sesión en curso), con el modelo que esté en uso:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  ```
- Descripciones de PR terminan con: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- `gh` está autenticado con la cuenta de quien trabaja (cada integrante tiene permiso de
  escritura); comprueba con `gh auth status` antes de abrir un PR.

## 9. Estado actual y plan de fases

El estado detallado y el calendario viven en el **maestro v2.4** (§0 y §8). Este resumen
es del 13-nov-2026; si choca con el maestro, gana el maestro.

- ✅ **Core OS:** ISO live + instalable (Calamares, LUKS2 argon2id, Secure Boot verificado),
  hermética (0 sospechosos, 0 listeners), <500 MB en reposo; 3C.2 idioma/zona/swap (#40).
- ✅ **Reproducibilidad:** MATCH ×2 en CI y entre máquinas físicas (H-001, H-004);
  espejo propio del snapshot (ADR-016). Cada commit cambia el SHA de la ISO (epoch del
  commit): "lo verificado sigue valiendo" se comprueba comparando contenido (squashfs + initrd).
- ✅ **LUKS + TPM:** `nimbo-tpm-setup` validado V2–V8 en QEMU (ADR-008); H-002 cerrado en
  QEMU con RAM mínima de 1 GiB (ADR-009). Falta hardware real (17-nov).
- ✅ **CLI `nimbo-audit`:** `init`/`capture`/`report`/`verify`, `.deb` (ADR-010) y dentro de
  la ISO (#42).
- ✅ **ISO integrada (ADR-020, #81 y #83):** `nimbo-nav` (Firefox ESR endurecido + modo Tor
  con `nimbo-leakcheck`), `nimbo-net` (WireGuard), `nimbo-red` (red por cable a demanda,
  ADR-019) y `nimbo-update-offline` dentro de la ISO; Tor y WireGuard no arrancan solos.
  ISO de la demo: `30b5958f…` (546 MiB), verificada en QEMU live e instalada.
- 🟡 **Validación por requisito sobre esa ISO:** RF-RED-01 en dos instalaciones (#84);
  RF-NAV-01/02 (Emmanuel) pendiente.
- 🟡 **Release firmado (ADR-015 Aceptado, `release.yml` en #78):** clave de release generada
  el 13-nov (huella en el `README.md`, clave pública en `release/`, #85) y environment
  `release` con sus tres secretos. Falta lanzarlo: candidato `03ff84c`, límite 17-nov
  16:11:04 UTC.
- ⏭️ **Prioridad Media, si da el tiempo (D15 = B):** RF-DIST-01, RNF-06.

**Requisitos vigentes:** el `.docx` "Requisitos de sistema" (15 RF + 7 RNF) y sus historias
de usuario. El criterio de aceptación lo manda ese documento; en fechas manda el plan de
trabajo. Los comentarios de `cli.py` aún usan la numeración antigua (RF-01, RF-03…).

**ADR 011–020 ya escritos.** Siguen en Propuesto: ADR-013 (air-gapped) y ADR-014
(hardening 3B.2, #69 abierto). El siguiente número libre es el 021.

**Jefes de nivel:** reproducibilidad (🏁) · Design Partner (🔴 sin cerrar) · LUKS + TPM
(✅ en QEMU; falta hardware real).

## 10. Decisiones abiertas (no las cierres tú)

Lista completa en el maestro v2.4 §12. Las que más afectan al trabajo diario:

- **D1 — Nombre real del proyecto:** 🔴 abierto (codename `nimbo` cubre el interín).
- **D2 — Design Partner:** 🔴 abierto.
- **D4 — Confirmar integrantes/autores en los docs SENA:** 🟠 antes de la entrega.
- **D16 — Fecha de sustentación:** 🔴 sin confirmar (plan a ~30-nov).
- (Resueltas: D7 codename = `nimbo` · D9 bookworm · D14 autologin solo live · D15 alcance
  por prioridad · D17 LUKS por contraseña + TPM opcional · D18 reparto en tres frentes ·
  dueño de RF-UPD-01 y RNF-03 = Juan José + IA, 10-nov.)

## 11. Anti-desborde — qué NO hacer sin que te lo pidan

- No adelantes fases. Termina lo pedido y para; si ves algo "necesario de una vez",
  **anótalo y menciónalo**, pero no lo hagas.
- No toques **configuración de GitHub** (protección de ramas, permisos, colaboradores) ni
  crees repos en la org: **eso es gestión humana.**
- No añadas dependencias, frameworks ni herramientas sin acordarlo.
- No introduzcas IA dentro del producto (principio de diseño).
- No inventes datos faltantes (usuarios, licencia, nombres): pregunta.
