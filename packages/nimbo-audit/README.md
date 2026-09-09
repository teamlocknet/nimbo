# packages/nimbo-audit

CLI de auditoría del sistema (`nimbo-audit`). Capa 3 del DAS (Python 3, patrones
**Command + Repository**, maestro §4.2). El **producto no lleva IA**.

**Dueño:** Juan José

## Estado (Paso 2B)

Esqueleto del paquete + subcomandos **`init`** (RF-01 / CU-01) y **`capture`**
(RF-03 / CU-02). `report` (2C) y el registro de sesión RF-02 (2B.2) son pasos
posteriores.

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

## Desarrollo

```
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[test]'
pytest -q
```
