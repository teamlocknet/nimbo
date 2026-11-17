# Manual — Registrar una auditoría con evidencia (`nimbo-audit`)

**Para:** quien audita con un equipo nimbo. **Requisitos:** RF-AUD-01 a RF-AUD-04, RNF-06.
**Diseño:** [ADR-010](../adr/ADR-010-empaquetado-nimbo-audit.md). **Detalle técnico:**
[`packages/nimbo-audit`](../../packages/nimbo-audit/README.md).

`nimbo-audit` guarda cada auditoría (un *caso*) en una carpeta propia y registra cada
evidencia con su **huella SHA-256**. Si alguien cambia o borra una evidencia después, el
sistema lo detecta. Funciona **sin red**.

## El ciclo completo (10 min)

Abre una terminal (menú → Terminal):

```
nimbo-audit init cliente-prueba            # 1. crea el caso en ~/audits/cliente-prueba/
cd ~/audits/cliente-prueba                 # 2. entra en el caso
nimbo-audit capture ~/evidencia1.txt       # 3. registra una evidencia (cualquier fichero)
nimbo-audit report                         # 4. informe en reportes/
nimbo-audit verify                         # 5. comprobación independiente
```

Lo que debe responder (medido en la ISO instalada, 16-nov):

```
[OK] Engagement 'cliente-prueba' inicializado en /home/<tu-usuario>/audits/cliente-prueba
[OK] Evidencia registrada: /home/<tu-usuario>/evidencia1.txt (SHA-256: 5555…d1d9)
[OK] Reporte generado en reportes/reporte-cliente-prueba.md
OK: evidencia1.txt
Resumen: 1 OK, 0 MODIFICADO, 0 AUSENTE
```

- `capture` **copia** el fichero dentro del caso (`evidencia/`); el original no se toca.
- Si un caso aún no tiene evidencias, `report` pregunta antes de generar un informe vacío
  (`--yes` para no preguntar).
- `report --pdf` también exporta a PDF si el equipo tiene `pandoc`; si no, avisa y deja el `.md`.

## Qué hay dentro de un caso

```
~/audits/cliente-prueba/
├── metadata.json        quién, cuándo
├── evidencia/           copias de las evidencias + index.json (nombre, SHA-256, hora)
├── reportes/            informes generados
├── logs/  notas/        para tu trabajo
```

## Comprobar que nada se tocó

`nimbo-audit verify` (dentro del caso, o `nimbo-audit verify <ruta-del-caso>`) recalcula la
huella de cada evidencia y la compara con la registrada. **No escribe nada en el caso.**

| Resultado | Significa | Código |
|---|---|---|
| `OK` | la evidencia es la misma que se registró | 0 si todas están OK |
| `MODIFICADO` | el fichero cambió después de registrarse | 1 |
| `AUSENTE` | el fichero ya no está | 1 |

Pruébalo: añade una línea a la copia guardada (`echo X >> evidencia/evidencia1.txt`) y vuelve
a ejecutar `nimbo-audit verify` → `MODIFICADO: evidencia1.txt`, `Resumen: 0 OK, 1 MODIFICADO,
0 AUSENTE` y código 1 (medido en la ISO, 16-nov).

## Errores frecuentes

| Si… | Qué hacer |
|---|---|
| el caso ya existe | elige otro nombre; `--force` lo **sobrescribe** (cuidado) |
| no se encuentra el caso activo | entra en la carpeta del caso (`cd ~/audits/<caso>`) o usa `--dir` |
| un nombre de evidencia ya registrado | `capture` no sobrescribe: renombra el fichero |

## Límites

- Solo comprueba las evidencias **registradas**. Si alguien cambia a la vez una evidencia y
  su huella en `index.json`, `verify` no lo detecta; tampoco acredita de dónde salió el fichero.
- No vigila notas, logs ni `metadata.json`.

## Cómo se verificó

Pruebas automáticas en CI con el Python de bookworm (job `tests-cli-bookworm`); ciclo
completo y alteración detectada en la ISO instalada sin red (RNF-03, Juan José, 16-nov) y otra
vez en la ISO de `main` `eb3bc36` siguiendo esta guía (Emmanuel, 16-nov).
