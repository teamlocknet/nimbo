# Matriz de trazabilidad — requisitos de nimbo `v1.0.0`

**Corte:** 21-nov-2026. **Fuente de los criterios:** documento "Requisitos de sistema" (15 RF y
7 RNF). **Versión:** `v1.0.0`, commit `94f9b8f`, ISO `63eeb31a…0f10`.

| Estado | Significa | Requisitos |
|---|---|---|
| ✅ | Criterio de aceptación cumplido y con evidencia versionada | **19** |
| 🟡 | Parte cumplida; se dice exactamente qué falta | **3** |
| 🔴 | Sin cumplir | **0** |

La columna **"Medido sobre"** importa: cada commit cambia el SHA de la ISO, así que no todo se midió
sobre la ISO exacta del release. Cuando es otra, se dice cuál.

## Requisitos funcionales

| Requisito | Prioridad | Criterio de aceptación | Estado | Resultado | Medido sobre | Evidencia |
|---|---|---|---|---|---|---|
| **RF-CORE-01** Arranque live | Alta | Llega al escritorio en VM UEFI | ✅ | Escritorio Xfce | `v1.0.0` | [21-nov](../../repro/evidencia/2026-11-21-live-y-licencias-v1.0.0.md) |
| **RF-CORE-02** Instalador | Alta | Ambos modos instalan y arrancan sin restos del instalador | ✅ | Cifrado y sin cifrar: `verificar-instalado` 0 fallos, sin restos del instalador | `v1.0.0` | [Cifrado](../../repro/evidencia/2026-11-20-qemu-instalado-94f9b8f.md), [sin cifrar](../../repro/evidencia/2026-11-21-qemu-sincifrar-94f9b8f.md) |
| **RF-CORE-03** Inicio de sesión | Alta | Muestra la pantalla de acceso y no entra solo | ✅ | Sin autologin | `v1.0.0` | [20-nov](../../repro/evidencia/2026-11-20-qemu-instalado-94f9b8f.md) |
| **RF-CORE-04** Endurecimiento | Alta | La verificación confirma cada ajuste en ISO e instalado | ✅ | `verify-hardening` 0 de 44 | Instalado: `v1.0.0` · Live: `7e405746` | [20-nov](../../repro/evidencia/2026-11-20-qemu-instalado-94f9b8f.md), [#83](../../repro/evidencia/2026-11-12-qemu-pr83.md) |
| **RF-CORE-05** LUKS2 | Alta | LUKS2 con argon2id; el arranque pide la contraseña | ✅ | LUKS2, `aes-xts-plain64`, argon2id | `v1.0.0` | [20-nov](../../repro/evidencia/2026-11-20-qemu-instalado-94f9b8f.md) |
| **RF-CORE-06** TPM | Media | En VM con TPM emulado abre solo y la contraseña sigue valiendo; sin LUKS2, mensaje claro | 🟡 | Criterio cumplido en QEMU, con el arreglo de GRUB. **El script no va dentro de la ISO** (se entrega por USB) y falta hardware real | `v1.0.0` + script de `main` · Sin LUKS2: `a4af6b8` | [21-nov](../../security/luks-tpm/evidencia/2026-11-21-pcr8-grub.md), [V3–V8](../../security/luks-tpm/evidencia/2026-11-04-V3-V8.md) |
| **RF-NAV-01** Navegador | Alta | No genera conexiones al abrirse en reposo | ✅ | 0 sospechosos en 120 s | `eb3bc36` | [16-nov](../../packages/nimbo-nav/evidencia/2026-11-16-iso-rf-nav.md) |
| **RF-NAV-02** Tor y fugas | Alta | Cero fugas durante la navegación | ✅ | 7 105 paquetes, 0 DNS, 0 fuera del túnel; fuga provocada detectada y avisada | `eb3bc36`; aviso: `42e95ae` | [16-nov](../../packages/nimbo-nav/evidencia/2026-11-16-iso-rf-nav.md), [19-nov](../../repro/evidencia/2026-11-19-medicion-101-103.md) |
| **RF-RED-01** Red privada | Alta | Dos equipos en un túnel cifrado con un comando cada uno | ✅ | 64/64 comprobaciones en dos instalaciones | `d114b8e` | [Resultados](../../packages/nimbo-net/pruebas/laboratorio/RESULTADOS-INTEGRADA.md) |
| **RF-AUD-01** `init` | Alta | Caso con estructura y metadatos, con pruebas automáticas | ✅ | 95 pruebas de `nimbo-audit` en CI | CI + ISO instalada | [Manual](../manuales/auditoria-con-evidencia.md) |
| **RF-AUD-02** `capture` | Alta | Cada evidencia queda con su hash | ✅ | SHA-256 en `index.json` | CI + ISO instalada | [Manual](../manuales/auditoria-con-evidencia.md) |
| **RF-AUD-03** `report` | Alta | Detecta el 100 % de las alteraciones de las pruebas | ✅ | OK, MODIFICADO y AUSENTE probados | CI + ISO instalada | [Manual](../manuales/auditoria-con-evidencia.md) |
| **RF-AUD-04** `verify` | Media | Un caso alterado falla y uno íntegro pasa | ✅ | Pasa. **Límite:** el índice no va firmado | CI + ISO instalada | [Validación](../manuales/validacion-verify.md) |
| **RF-UPD-01** Actualización | Alta | Rechaza el 100 % de las firmas inválidas | ✅ | 14 de 14 lotes inválidos rechazados, sin red | `7d0da21c` (#89) | [16-nov](../../repro/evidencia/2026-11-16-rnf03-sin-red.md) |
| **RF-DIST-01** Distribución | Media | La 1.0 se descarga, se verifica y se instala desde el repositorio | 🟡 | Release y APT `v1.0.0` publicados y firmados. **Falta instalar desde el APT en una VM limpia** | Publicado | [Release](https://github.com/teamlocknet/nimbo/releases/tag/v1.0.0), [APT](https://teamlocknet.github.io/nimbo/apt/) |

## Requisitos no funcionales

| Requisito | Prioridad | Criterio de aceptación | Estado | Resultado | Medido sobre | Evidencia |
|---|---|---|---|---|---|---|
| **RNF-01** Hermetismo | Alta | Cero conexiones salientes y cero puertos en reposo | ✅ | Live: 0 sospechosos y 0 listeners. Instalado: 0 DNS, NTP, web o SYN | `v1.0.0` | [21-nov](../../repro/evidencia/2026-11-21-live-y-licencias-v1.0.0.md), [20-nov](../../repro/evidencia/2026-11-20-qemu-instalado-94f9b8f.md) |
| **RNF-02** RAM | Alta | Menos de 500 MB en reposo, live e instalado | ✅ | Live **376 MiB** · Instalado **395 MiB** | `v1.0.0` | [21-nov](../../repro/evidencia/2026-11-21-live-y-licencias-v1.0.0.md), [20-nov](../../repro/evidencia/2026-11-20-qemu-instalado-94f9b8f.md) |
| **RNF-03** Sin internet | Alta | Instalación y uso de cada módulo en VM sin red | ✅ | Instalación sin red y 5 módulos, 0 fallos de 37 | `7d0da21c` (#89) | [16-nov](../../repro/evidencia/2026-11-16-rnf03-sin-red.md) |
| **RNF-04** Software libre, costo cero | Alta | Todo con licencia libre y costo de infraestructura cero | ✅ | 557 + 38 paquetes, todos en `main`. Costo cero confirmado por Juan José (21-nov) | `v1.0.0` | [21-nov](../../repro/evidencia/2026-11-21-live-y-licencias-v1.0.0.md) |
| **RNF-05** Plataforma | Alta | Pruebas en Python 3.11 y arranque en VM UEFI | ✅ | 311 pruebas de Python + 8 de compilación, en Python 3.11.2 | CI de `main` + `v1.0.0` | [21-nov](../../repro/evidencia/2026-11-21-live-y-licencias-v1.0.0.md) |
| **RNF-06** Usabilidad | Media | El Design Partner instala y usa solo con la guía, en una jornada | 🟡 | Cada módulo tiene guía (CA-2). **Falta la validación de una persona externa** (CA-1) | — | [Guías](../manuales/guias-de-uso.md) |
| **RNF-SEC-07** Reproducibilidad | Alta | Mismo SHA-256 en dos compilaciones independientes | ✅ | MATCH ×2 de la ISO del release | `v1.0.0` | [Run 44654170829](https://github.com/teamlocknet/nimbo/actions/runs/44654170829), [20-nov](../../repro/evidencia/2026-11-20-qemu-instalado-94f9b8f.md) |

## Qué falta para cerrar los tres 🟡

| Requisito | Falta | Quién |
|---|---|---|
| RF-CORE-06 | Prueba en hardware real. Decidir si el script entra en una versión posterior de la ISO | Juan José |
| RF-DIST-01 | Validar el corte `v1.0.0` del APT en una VM limpia | Alejandro |
| RNF-06 | Validación con una persona externa | Juan José |

## Límites declarados

- Todo lo anterior se midió en QEMU o VM. **Ningún requisito se ha verificado aún en hardware real.**
- RF-AUD-04: el índice de evidencias no va firmado, así que `verify` compara contra lo registrado.
- RF-UPD-01: un lote viejo pero bien firmado sigue siendo válido; `apt` se niega a bajar de versión,
  pero falta repetir esa prueba con un lote firmado y sin red.
- RF-NAV-02: evita fugas de red; no protege frente a la huella del navegador.
