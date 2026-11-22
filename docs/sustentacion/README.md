# Material de sustentación

Una página por módulo para la presentación final: **qué hace, cómo se prueba, qué se midió y
qué hallazgos salieron**. Cada cifra sale de una evidencia versionada en el repositorio (se cita
al pie de cada página). Lo que todavía no se ha medido sobre la ISO integrada se dice así.

| Página | Requisitos |
|---|---|
| [Navegación segura](navegacion-segura.md) | RF-NAV-01, RF-NAV-02 |
| [Endurecimiento del sistema (3B.2)](endurecimiento-3b2.md) | RF-CORE-04 |
| [Actualización sin conexión](actualizacion-sin-conexion.md) | RF-UPD-01 |
| [Núcleo y reproducibilidad](nucleo-reproducibilidad.md) | RF-CORE-01/02/03/05, RNF-01/02/03/05, RNF-SEC-07 |
| [Desbloqueo con TPM](desbloqueo-tpm.md) | RF-CORE-06 |
| [Auditoría con evidencia](auditoria.md) | RF-AUD-01 a RF-AUD-04 |
| [Red privada del equipo](red-privada.md) | RF-RED-01 |
| [Distribución firmada](distribucion.md) | RF-DIST-01 |

Las páginas de navegación, endurecimiento y actualización son obra de **Emmanuel Cardozo**
([créditos](../../CREDITOS.md)).

**Hilo para contarlo en la sustentación:** en esos tres módulos, la prueba se escribió antes que
el código (rojo → verde), y cada vez que se probó en un Debian real apareció algo que las
pruebas unitarias no podían ver: rutas que Firefox no leía, un fichero de `procps` que pisaba un
parámetro, un falso positivo de DHCP. Encontrarlos y corregirlos con evidencia es la garantía.

## Versión que se presenta

[`v1.0.0`](https://github.com/teamlocknet/nimbo/releases/tag/v1.0.0): commit `94f9b8f`, ISO
`63eeb31a33c4a9d4a6597573a6f567d66b6afbbb207286ae7920197414cc0f10`. Instalada en QEMU con Secure
Boot y LUKS el 20-nov: `verificar-instalado` 0 fallos, `verify-hardening` 0 de 44 y 395 MiB en
reposo ([evidencia](../../repro/evidencia/2026-11-20-qemu-instalado-94f9b8f.md)).

## Huella de la clave de release

Segundo canal independiente de la huella (ADR-015); el primero es el README del repositorio.
Quien verifique un release compara la huella de su `release-key.asc` con esta:

- Huella primaria: `0C50 B739 1A9B 8CFF 8A36  A627 D3B9 111F EC57 48C6`
