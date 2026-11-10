# ADR-018 — Firmware explícito: sin firmware deducido de Contents

**Estado:** Aceptado (10-nov, Juan José) · **Paso:** 3B.2 (núcleo de la ISO)

## Contexto

live-build activa por defecto `--firmware-chroot true`: en la etapa `chroot_firmware`
descarga el índice `Contents-{all,amd64}` de `main` (45 MB) y marca para instalar todo
paquete que tenga ficheros en `lib/firmware/`. Con `--archive-areas "main"` salían 8
candidatos y entraban 6. Medido el 10-nov con el `dpkg/status` del chroot (quitar esos
paquetes y todo lo que solo existía como dependencia suya):

| Qué | Paquetes |
|---|---|
| Firmware de hardware concreto | `firmware-ath9k-htc` (memorias USB Wi-Fi Atheros AR9271/AR7010), `wireless-regdb` (normas de radio del Wi-Fi), `hdmi2usb-fx2-firmware` y `ixo-usb-jtag` (placas Cypress FX2, cables JTAG) |
| `indi-dsi` (cámaras de astronomía Meade DSI) y lo que arrastra | `libindidriver1`, `libindi-data`, `libcfitsio10`, `libnova-0.16-0`, `libfftw3-double3`, `libgomp1`, `libtheora0`, `libusb-1.0-0` y, vía `libcfitsio10`, **`libcurl3-gnutls`, `libssh2-1`, `librtmp1`, `libnghttp2-14`, `libpsl5`** |
| Total | **18 paquetes, 12.3 MiB instalados (≈ 3.8 MiB en `.deb`)**, en el live **y** en el sistema instalado |

`firmware-linux-free` y `alsa-topology-conf` también son candidatos, pero los piden otros
paquetes: se quedan. `jh7100-bootloader-recovery` es solo RISC-V.

Problemas:

- **Superficie sin uso:** cinco bibliotecas de red (el mismo argumento que `libcurl4` en
  ADR-008) para unas cámaras de astronomía.
- **Entrada frágil del build:** el 8-nov, cuando el espejo (ADR-016) rechazaba la doble
  barra, live-build no obtuvo `Contents` y la etapa **no instaló nada sin dar error**: la
  ISO cambió en silencio. El contenido de la ISO dependía de un índice de 45 MB que nadie
  revisa.
- **Principio "el determinismo primero":** lo que entra en la ISO debe estar escrito en la
  receta, no deducido.

## Opciones

| Opción | A favor | En contra |
|---|---|---|
| A. Dejarlo como está | Cero cambios | Todo lo anterior |
| **B. `--firmware-chroot false` + `--firmware-binary false`; el firmware que haga falta se lista a mano** | Receta explícita; 18 paquetes y 5 bibliotecas de red menos; una descarga y un fallo silencioso menos | Se pierde el firmware de arriba (ver Consecuencias). Cambia el SHA de la ISO |
| C. Mantenerlo y excluir paquetes uno a uno | Conserva el resto del firmware deducido | Sigue dependiendo de `Contents`; lista negra que hay que mantener |

`--firmware-binary` solo añade firmware para el instalador de Debian; con
`--debian-installer none` no hace nada. Se desactiva para que la receta diga lo que hace.

## Decisión

**B.** La receta pasa `--firmware-chroot false` y `--firmware-binary false`. Si un equipo
real necesita un firmware de `main`, se añade a mano a una lista de
`config/package-lists/`, con su motivo.

## Consecuencias

- **Se pierde:** Wi-Fi por memorias USB Atheros (Wi-Fi ya está fuera de v1: no hay
  `wpasupplicant`, ver ADR-012), placas FX2/JTAG y cámaras DSI. **Nada** de arranque, disco,
  pantalla, red por cable ni TPM.
- **No cambia (riesgo aparte para el hardware real):** el firmware que importa en portátiles
  (Realtek `rtl_nic`, Wi-Fi Intel, GPU AMD) está en `non-free-firmware`, que la receta no
  activa. En la prueba del 17-nov hay que mirar `dmesg | grep -i firmware`.
- **Cambia el SHA de la ISO:** compuerta MATCH ×2 en el PR. La línea base 3B.1
  (`paquetes-linea-base-3b1.txt`) pierde esas 18 líneas.
- **Verificación:** `tests/test-sin-firmware-deducido.sh` (receta y línea base, en CI);
  sobre la ISO de CI, lista de paquetes sin los 18, hermetismo 0/0 y RAM < 500 MB;
  `verificar-instalado` en QEMU.

## Fecha

2026-11-10
