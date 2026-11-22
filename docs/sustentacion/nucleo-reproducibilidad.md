# Núcleo del sistema y reproducibilidad — RF-CORE-01/02/03/05, RNF-01/02/03/05 y RNF-SEC-07

**Responsable:** Juan José.

## Qué hace

- **Un Debian 12 que se instala cifrado.** ISO live con escritorio Xfce e instalador gráfico en
  español, con dos modos: cifrado con LUKS2 (recomendado) y sin cifrar (avanzado).
- **No habla con nadie si no se lo piden.** Arranca sin red, sin puertos abiertos y sin
  actualizaciones automáticas.
- **Reproducible bit a bit.** La misma receta produce el mismo fichero, con el mismo SHA-256. Así,
  un tercero puede comprobar que la ISO publicada sale de este código y de nada más.

## Cómo se prueba

| Qué | Prueba |
|---|---|
| Reproducibilidad | Compuerta de CI: **dos compilaciones** en máquinas efímeras distintas; si el SHA-256 no coincide, no pasa |
| Otro anfitrión | La misma ISO compilada en un PC físico con otro sistema operativo y otro sistema de archivos |
| Hermetismo | Captura de todo el tráfico de la VM desde el hipervisor, 120 s en reposo |
| RAM | Medición automática en VM de 2 GiB tras el reposo |
| Sistema instalado | `verificar-instalado --secure-boot`: cifrado, arranque, autologin, paquetes y módulos |
| Sin internet | VM **sin tarjeta de red**: instalación completa y uso de cada módulo |

## Qué se midió sobre `v1.0.0`

| Medida | Resultado |
|---|---|
| Reproducibilidad | **MATCH ×2**: `63eeb31a…0f10` en las dos compilaciones |
| Tamaño de la ISO | **546 MiB** |
| RAM en reposo | Live **376 MiB** · Instalado **395 MiB** (límite: 500 MB) |
| Hermetismo live | **0 sospechosos, 0 puertos** (12 paquetes, todos de arranque de la tarjeta) |
| Hermetismo instalado | **0 DNS, 0 NTP, 0 web, 0 SYN** (2 paquetes IPv6 de enlace) |
| Instalación cifrada con Secure Boot | `verificar-instalado`: **0 fallos** |
| Instalación sin cifrar con Secure Boot | `verificar-instalado`: **0 fallos**, 388 MiB en reposo |
| Licencias | 557 paquetes instalados y 38 en el pool, **todos en `main`** |

## Hallazgos

1. **La verificación detectó una filtración real del anfitrión (H-001).** Al compilar en un PC con
   btrfs, el SHA dejó de coincidir con CI. Se localizó hasta un único campo (`nlink`) del initrd,
   que dependía del sistema de archivos. Con el initrd sobre `tmpfs` (ADR-007), el PC físico y CI
   dan **el mismo SHA-256**.
2. **El SHA dependía de la fecha de los ficheros (H-004).** El mismo commit daba un SHA en una copia
   de trabajo y otro en un clon nuevo, por las fechas de 36 entradas. Ahora se fijan al compilar.
3. **Depender de un servicio externo rompía la compuerta (ADR-016).** `snapshot.debian.org` tumbó 9
   compilaciones en dos días. Se creó un espejo propio de los mismos paquetes.
4. **RAM mínima para descifrar (H-002).** Un disco instalado con mucha RAM no abría en un equipo con
   poca, y el error parecía de contraseña. Se fijó el mínimo en **1 GiB** instalando en la propia
   máquina y el mensaje ahora dice la causa real (ADR-009).

## Lo que falta

- **Hardware real:** todo lo anterior se midió en QEMU.
- RNF-03 se midió sobre la ISO de #89 (`7d0da21c`), no sobre la del release.

*Evidencia:* `repro/evidencia/2026-11-20-qemu-instalado-94f9b8f.md`,
`repro/evidencia/2026-11-21-qemu-sincifrar-94f9b8f.md`,
`repro/evidencia/2026-11-21-live-y-licencias-v1.0.0.md`,
`repro/evidencia/2026-11-16-rnf03-sin-red.md`,
`repro/evidencia/2026-10-23-match-entre-anfitriones.md` · *Hallazgos:* `docs/hallazgos/` ·
*Diseño:* ADR-004, ADR-006, ADR-007, ADR-009 y ADR-016
