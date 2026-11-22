# Auditoría con evidencia (`nimbo-audit`) — RF-AUD-01 a RF-AUD-04

**Responsable:** Alejandro.

## Qué hace

- **`init`** crea un caso con estructura fija: metadatos, evidencia, informes, registros y notas.
- **`capture`** copia cada evidencia dentro del caso y guarda su **SHA-256** y su hora. Nada se
  sobrescribe en silencio: un nombre ya registrado se rechaza.
- **`report`** genera un informe que marca cada evidencia como OK, MODIFICADO o AUSENTE.
- **`verify`** deja que un tercero compruebe el caso **sin modificarlo**.

Funciona sin red. Está diseñado con los patrones **Command** (una clase por subcomando) y
**Repository** (abstrae el sistema de archivos).

**Límite que se declara tal cual:** el índice de evidencias **no va firmado**. `verify` detecta un
cambio en una evidencia, pero quien reescriba la evidencia **y** su hash en el índice puede evadirlo.
No prueba autenticidad.

## Cómo se prueba

| Qué | Prueba |
|---|---|
| Ciclo completo | Pruebas automáticas en CI, con el Python 3.11 de bookworm |
| Alteraciones | Un byte cambiado, evidencia borrada, hash mal formado, índice inválido |
| Rutas peligrosas | Rutas externas y enlaces que salen del caso, duplicados |
| "Sin modificarlo" | Manifiesto del caso igual antes y después: rutas, tipos, permisos, fechas y hashes |
| Sobre el producto | Ciclo completo en la ISO instalada |

## Qué se midió

| Medida | Resultado |
|---|---|
| Pruebas automáticas | **95 pasan** (45 son de `verify`) |
| Evidencia íntegra | `OK`, código 0 |
| Evidencia alterada | `MODIFICADO`, código 1 |
| Evidencia borrada | `AUSENTE`, código 1 |
| En la ISO instalada (16-nov) | Ciclo completo y alteración detectada |
| En `v1.0.0` instalada | `nimbo-audit` 0.1.0-1, con `verify` y su manual |

## Hallazgos

1. **La prueba también se prueba:** una ejecución falló porque el test de "permiso denegado"
   simulaba una función distinta de la que usa el cálculo del hash. Se corrigió la simulación y se
   repitió toda la batería.
2. **Rojo antes del código:** `verify` se escribió con su prueba fallando primero (1 fallo, 50 en
   verde) y terminó en 95 en verde.

## Lo que falta

Los cuatro criterios de aceptación se cumplen. Queda declarado el límite del índice sin firmar.

*Evidencia:* `docs/manuales/validacion-verify.md`, `docs/manuales/validacion-cli-en-iso.md` ·
*Diseño:* ADR-010 · *Manual:* `docs/manuales/auditoria-con-evidencia.md`
