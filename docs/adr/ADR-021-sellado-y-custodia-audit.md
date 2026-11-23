# ADR-021 — Sellado y cadena de custodia en `nimbo-audit` 0.2.0

**Estado:** Propuesto (22-nov, plan aprobado por Juan José; se acepta tras validarlo en la ISO
instalada) · **Dueño:** Juan José

## Contexto

`nimbo-audit` 0.1.0 detecta cambios accidentales y manipulaciones torpes, pero no prueba que nadie
alterara la evidencia a propósito:

1. `evidencia/index.json` no está protegido: quien reescribe la evidencia y su hash obtiene `OK`.
2. La hora sale del reloj del equipo.
3. `analista` es el usuario del sistema.
4. No hay registro de acciones ni origen de cada archivo.
5. Un archivo metido a mano en `evidencia/` no se señala y las copias se pueden editar.

La ISO de `v1.0.0` ya está firmada y no debe cambiar antes del simulacro del 25-nov. La sesión
live trae `gpg`, `gpg-agent` y `pinentry-curses`, pero el instalador los retira como huérfanos:
el sistema **instalado** solo conserva `gpgv` y no puede obtener los demás sin red.

## Decisión

Añadir custodia en `custodia/`, sin cambiar el formato de `evidencia/index.json`:

- **Registro encadenado** (`registro.jsonl`): cada acción guarda quién, qué, cuándo, el origen de la
  evidencia y el hash de la entrada anterior.
- **Sello** (`nimbo-audit seal --clave <huella>`): `sello.json` lista el SHA-256 de **todos** los
  archivos del caso y se firma con GPG. Después, el caso no admite cambios.
- **Clave por analista.** Se exige la huella completa y se rechaza la clave de release.
- **Ancla externa:** el SHA-256 de `sello.json` se entrega al cliente por otro canal.
  `verify --ancla` o `--huella` comprueban contra ese dato.
- **`verify` más estricto:** señala archivos no registrados, registro roto y sello roto.
- **Copias de evidencia en modo 0440.**
- Los casos de 0.1.0 se siguen verificando como `SIN REGISTRO` y `SIN SELLAR`. Al capturar,
  reportar o sellar, entran en custodia con una entrada `adopcion`.
- Se entrega como **0.2.0 por lote firmado**, sin tocar la ISO de `v1.0.0`. El lote **debe incluir**
  `gpg`, `gpg-agent`, `gpgconf`, `pinentry-curses`, `libassuan0` y `libnpth0`.

## Consecuencias

- Reescribir evidencia, índice y registro de forma coherente rompe el sello.
- **Sin ancla o huella, un sello válido solo prueba coherencia.** Quien controle el equipo podría
  borrar el sello y volver a sellar con otra clave. `verify` lo avisa.
- **La hora sigue siendo la del equipo.** Sin red no se puede garantizar.
- `--analista` y `--origen` son **declaraciones**. Lo único que identifica de forma verificable es
  la clave que firma, y solo si su huella se conoce por otro canal.
- El registro no impide truncar la cola de un caso sin sellar si el índice sigue coincidiendo.
- Una clave caducada solo se acepta con `--ancla`. Una clave revocada invalida el sello.
- Un caso sellado no se puede ampliar: el trabajo posterior va en un caso nuevo.
- `gpg`, `gpg-agent` y `gpgv` pasan a ser dependencias del paquete. Instalar `gpg-agent` habilita
  sus sockets de usuario, así que el hermetismo debe medirse otra vez con el lote aplicado.

## Validación

Sello y ataque en la ISO instalada, y lote instalado con `apt` en una copia limpia:
[evidencia del 22-nov](../../packages/nimbo-audit/evidencia/2026-11-22-custodia-iso-instalada.md).
Falta aplicar el lote firmado con `nimbo-update-offline`.

## Fecha

2026-11-22
