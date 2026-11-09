# ADR-017 — Instalador: idioma, zona horaria, swap y particionado (3C.2)

**Estado:** Aceptado (8-nov, Juan José)

## Contexto

En 3C.1 (ADR-006) el instalador se dejó deliberadamente mínimo:

- **Sin pantalla de idioma/zona** (`locale`/`localecfg` fuera, sin el paquete `locales`) para no
  usar geoip. Resultado: el sistema instalado queda en `LANG=C.UTF-8` y `Etc/UTC` (leído el
  8-nov del disco sin cifrar del 3-nov). Para un equipo de auditoría en Colombia, la hora de
  la evidencia y de los logs en UTC y los mensajes en inglés son un problema de uso.
- **Sin swap**: una partición de swap en claro filtraría memoria al disco. Con el mínimo de
  1 GiB de RAM (H-002, ADR-009) la falta de swap deja poco margen.
- **Sin particionado manual**: el arranque (GRUB lee `/boot` en claro) y `nimbo-tpm-setup`
  (ADR-008) dependen de la estructura ESP + `/boot` ext4 en claro + raíz ext4 sobre LUKS2.

Calamares 3.3.8 (comprobado en el paquete del snapshot): el módulo `locale` lista los idiomas
de `/usr/share/i18n/SUPPORTED` y admite `geoip: style: none`; `localecfg` descomenta el idioma
elegido en `/etc/locale.gen` del destino y ejecuta `locale-gen`; con `userSwapChoices: file`
el módulo `fstab` crea `/swapfile` de **512 MiB** en la raíz y lo añade a `fstab`.

## Decisión

Decidido por Juan José el 8-nov (las tres recomendaciones):

1. **Idioma y zona: pantalla de Calamares, sin red.** `locale` en la secuencia (show y exec) y
   `localecfg` en exec. `locale.conf`: `geoip: style: none`, sin `url`, zona por defecto
   `America/Bogota` (Calamares propone `es_CO.UTF-8` por el país), `adjustLiveTimezone: false`.
   El paquete `locales` entra en `desktop.list.chroot` (live e instalado). La lista de idiomas
   es la completa de `SUPPORTED`; en el destino solo se genera el elegido.
2. **Swap: archivo dentro de la raíz cifrada.** `userSwapChoices: [ none, file ]`,
   `initialSwapChoice: file`. En la instalación cifrada, `/swapfile` vive dentro del volumen
   LUKS2. **La variante sin cifrar (hook 0190) pasa a `none`**: un archivo de swap en claro
   filtraría memoria. Nunca partición de swap.
3. **Particionado manual: no en v1.** `allowManualPartitioning: false` se mantiene; queda como
   decisión, no como deuda.

## Cómo se verifica

- `iso/live-build/tests/test-requisitos-calamares.sh` (CI): locale en show/exec, localecfg,
  geoip `none` sin url, `locales` en la lista, swap `file`. Rojo (7 fallos) → verde.
- `iso/live-build/verificar-instalado.sh`, sección 6: `LANG` elegido **y** generado
  (`locale -a`), zona distinta de UTC, `/swapfile` activo **sobre `/dev/mapper/*`** y en
  `fstab`; con `--sin-cifrar`, ninguna swap. Rojo comprobado en el disco del 3-nov.
- Build: el hook 0190 falla si la transformación de swap no aplica. Compuerta MATCH ×2.
- QEMU: hermetismo del live (pcap: 0 sospechosos, 0 listeners) con la pantalla nueva; RAM en
  reposo < 500 MB; instalación con 1024 MiB (que `locale-gen` y la swap no rompan H-002).

## Resultados (8-nov, QEMU + Secure Boot, ISO local `893276f1…` = rama del PR #40)

| Prueba | Resultado |
|---|---|
| `test-requisitos-calamares.sh` | rojo 7/7 → verde 10/10; CI del PR en verde con MATCH ×2 |
| Hermetismo del live en reposo (`verify-hermetismo-in-qemu.sh`) | ✅ 0 sospechosos · 0 listeners |
| RAM en reposo del live (`measure-ram-in-qemu.sh`) | ✅ 370 MiB (< 500 MB; antes 366 MiB) |
| **Instalación completa con captura de red** (`NIMBO_PCAP`, 4 GiB) | ✅ 18 paquetes, todos de arranque de red (DHCP, ARP, NDP IPv6): **0 DNS, 0 NTP, 0 web, 0 SYN**. La pantalla de idioma/zona no sale a la red |
| Pantallas (vistas por Juan José) | nueva pantalla de ubicación con Bogotá / español (Colombia); en el particionado, swap en archivo y "sin swap" |
| `verificar-instalado.sh --secure-boot` (log serie) | ✅ `VEREDICTO: OK — 0 fallos`: `LANG=es_CO.UTF-8` generado · zona `America/Bogota` · `/swapfile` 513M activo **dentro de `/dev/mapper/luks-…`** y en `fstab` |
| RAM en reposo del instalado (misma sección, 90 s) | 384 MiB (< 500 MB) |
| Instalación y arranque con **1024 MiB** | ✅ instala, desbloquea a la primera (Juan José); keyslot argon2id 448 726 KiB, t=8 (igual que en H-002); sin OOM en el log de la instalación |

## Consecuencias

- El instalado queda en el idioma y la hora del usuario; los timestamps locales de la
  evidencia (`nimbo-audit`) dejan de estar en UTC sin que nadie lo haya elegido.
- `locales` añade unos MB a la ISO y live-config genera el idioma de la sesión live al arrancar
  (medir la RAM en reposo).
- Swap de 512 MiB fija (la decide Calamares); suficiente como colchón en 1 GiB. No ayuda al
  desbloqueo de H-002, que ocurre en el initramfs, antes de montar la raíz.
- Sin particionado manual: no hay arranque dual guiado ni esquemas a medida en v1.
- La hora del sistema sigue el reloj de hardware en UTC (módulo `hwclock`); solo cambia la zona.

## Fecha

2026-11-08
