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


### `verify` (RF-AUD-04 / HU-13)

```bash
nimbo-audit verify [RUTA_DEL_CASO]
```

Comprueba la integridad sin escribir en el caso. Con ruta, usa ese caso;
sin ruta, busca el engagement activo subiendo desde el directorio actual.
No necesita que el directorio del caso conserve su nombre original.

Por cada evidencia del indice imprime **OK**, **MODIFICADO** o **AUSENTE**,
con su nombre, y un resumen. Un SHA-256 mal formado aparece como MODIFICADO
con un diagnostico del indice. Los hashes hexadecimales en mayusculas se
aceptan. No se actualizan hashes ni se reparan archivos.

- Salida **0**: todas las evidencias registradas coinciden. Un indice valido
  con lista vacia devuelve 0 y un resumen de cero archivos.
- Salida **1**: evidencia modificada/ausente, hash mal formado o caso/indice
  que no se puede verificar (invalido, ausente o ilegible).
- Los errores de sintaxis del comando usan el codigo del parser (**2**).

El indice debe existir: un caso recien creado por init que todavia no tiene
evidencia/index.json falla explicitamente, en lugar de declararse integro.
Se rechazan versiones desconocidas, entradas incompletas o duplicadas y rutas
que no correspondan a evidencia/<nombre>, incluidas referencias fuera del
caso mediante enlaces. No se siguen enlaces del indice o metadata al exterior.
Los fallos estructurales abortan con [ERROR]; no se presenta un resumen
parcial como si verificara el caso completo.

**Limites:** se verifica solo la evidencia registrada. Si alguien reescribe
a la vez la evidencia y su hash en el indice, verify no lo detecta. Tampoco
acredita el origen del archivo; firmar el indice queda fuera del alcance.
No inventaria archivos no registrados, no verifica los hashes de notas,
metadata o logs, ni garantiza una instantanea si otro proceso cambia el caso
durante la lectura. Leer puede actualizar atime segun el sistema de archivos;
la herramienta no escribe contenido ni genera reportes o logs.

El registro de sesion RF-02 del ERS antiguo no forma parte de este subcomando.
Su codigo existente no se elimina ni se implementa en A5.

## Desarrollo

```
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

El venv local sirve para iterar rápido, pero **no prueba el producto**: la ISO es offline
y el CLI corre con las versiones de bookworm (ADR-005: Python 3.11, typer 0.7, click 8.1,
pytest 7.2). Para probar contra ellas, en el mismo contenedor anclado que la ISO y con
las dependencias instaladas desde APT:

```
CONTAINER_ENGINE=docker ./test-in-bookworm.sh    # o podman (por defecto)
```

Es lo mismo que corre el job `tests-cli-bookworm` del CI. Los tests usan el fixture
`cli_runner` (`tests/conftest.py`), que separa stderr tanto en click 8.1 como en 8.2+.
