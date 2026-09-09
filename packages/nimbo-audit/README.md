# packages/nimbo-audit

CLI de auditoría del sistema (`nimbo-audit`). Capa 3 del DAS (Python 3, patrones
**Command + Repository**, maestro §4.2). El **producto no lleva IA**.

**Dueño:** Juan José

## Estado (Paso 2A)

Esqueleto del paquete + subcomando **`init`** (RF-01 / CU-01). `capture` (2B) y
`report` (2C) son pasos posteriores.

```
nimbo-audit init <cliente> [--dir <base>] [--force]
```

Crea el engagement estandarizado (§4.3) en `~/audits/<cliente>/` (o en `--dir`):
`evidencia/ logs/ reportes/ notas/` + `metadata.json` (id · fecha/hora inicio ·
analista=usuario del sistema). No sobrescribe un engagement existente salvo
`--force` (destructivo, acotado al directorio base). `--dir` sirve para pruebas
herméticas sin tocar el home real.

## Desarrollo

```
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[test]'
pytest -q
```
