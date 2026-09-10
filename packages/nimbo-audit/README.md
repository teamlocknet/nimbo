# packages/nimbo-audit

CLI de auditoría del sistema (`nimbo-audit`). Capa 3 del DAS (Python 3, patrones
**Command + Repository**, maestro §4.2). El **producto no lleva IA**.

**Dueño:** Juan José

## Estado (Paso 2C)

Ciclo del CLI completo: **`init`** (RF-01 / CU-01), **`capture`** (RF-03 / CU-02)
y **`report`** (RF-04 / CU-03). El registro de sesión RF-02 (2B.2) es un paso
posterior; `report` solo lo consume si existe y tolera su ausencia.

### `init`

```
nimbo-audit init <cliente> [--dir <base>] [--force]
```

Crea el engagement estandarizado (§4.3) en `~/audits/<cliente>/` (o en `--dir`):
`evidencia/ logs/ reportes/ notas/` + `metadata.json` (id · fecha/hora inicio ·
analista=usuario del sistema). No sobrescribe un engagement existente salvo
`--force` (destructivo, acotado al directorio base). `--dir` sirve para pruebas
herméticas sin tocar el home real.

### `capture`

```
nimbo-audit capture <archivo> [--dir <raíz-engagement>]
```

Copia `<archivo>` a `evidencia/` del engagement **activo**, calcula su SHA-256
(por streaming, memoria acotada) y registra `ruta + sha256 + timestamp` en
`evidencia/index.json`. El engagement activo se detecta **subiendo desde el
directorio actual** hasta hallar un `metadata.json`; `--dir` lo apunta directo
(útil en pruebas y scripting).

Integridad (Casos de Uso §4): nada se sobrescribe en silencio — un nombre ya
registrado se rechaza; el `sha256` almacenado es el ancla que delata cualquier
modificación posterior. El índice se escribe de forma atómica (temporal +
rename) con rollback de la copia si algo falla. Ante restricción de memoria
(RNF-08) aborta con `[AVISO]` limpio, sin traceback y sin corromper el estado.

### `report`

```
nimbo-audit report [--dir <raíz-engagement>] [--pdf] [--yes]
```

Consolida el engagement **activo** (misma resolución que `capture`) en
`reportes/reporte-<id>.md`, en tres secciones: **datos del engagement** (leídos
vía repositorio), **cronología de la sesión** (lista los registros de `logs/` si
existen; RF-02 pendiente, su ausencia se tolera) y **evidencia registrada** con
su SHA-256.

**Verificación de integridad (la otra mitad del valor probatorio):** al
consolidar, `report` recomputa el SHA-256 de cada archivo de evidencia y lo
compara con el hash ancla del índice, marcando cada fila como **OK**,
**MODIFICADO** (el archivo existe pero cambió) o **AUSENTE** (ya no está en
disco), más un resumen. El `.md` es **determinista** (no usa reloj de pared):
mismo engagement → mismo texto.

Si el engagement no tiene evidencia ni registros de sesión (CU-03 1a), avisa y
pide confirmación antes de generar un reporte incompleto (`--yes` la salta).

**PDF (`--pdf`, opcional):** el `.md` es el entregable primario; `--pdf` exporta
además a PDF por shell-out a `pandoc` (FOSS, **sin dependencia Python**). Si
pandoc no está, o está pero falta su motor PDF (LaTeX/wkhtmltopdf), degrada con
gracia: emite un `[AVISO]` y genera igualmente el `.md` (nunca revienta).

## Desarrollo

```
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[test]'
pytest -q
```
