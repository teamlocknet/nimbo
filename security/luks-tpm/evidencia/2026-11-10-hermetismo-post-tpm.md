# Hermetismo tras `nimbo-tpm-setup` — QEMU + swtpm (2026-11-10)

**Estado:** ✅ OK. Un sistema que ya pasó por `nimbo-tpm-setup` (fases 1 y 2, con
`libcurl4` instalada) no hace ninguna conexión saliente y no tiene ningún puerto
escuchando. Cierra el pendiente de ADR-008. Falta repetirlo en hardware real (17-nov).

## Por qué se mide

La fase 1 de `nimbo-tpm-setup` instala dracut, tpm2-tools y las libtss2. `libtss2-fapi1`
arrastra `libcurl4`, una biblioteca de red que no estaba en la línea base. Hay que
comprobar que su presencia no cambia nada: 0 conexiones y 0 puertos escuchando.

## Entorno

- Disco `iso/live-build/nimbo-install-sb-tpm.qcow2`: instalado el 4-nov desde la ISO de
  CI `17ee64c8…1da0` (commit `a4af6b8`) con el lanzador cifrado. Es el mismo disco de las
  pruebas V3–V8 (`2026-11-04-V3-V8.md`), con el token `systemd-tpm2` sellado (PCR 7+9).
- Arranque: `NIMBO_PCAP=<fichero> NIMBO_QEMU_MONITOR=<socket> ./install-in-qemu.sh
  --secure-boot --tpm arrancar` (OVMF de Debian, `SecureBoot=1`, swtpm persistente).
- Captura: `filter-dump` de QEMU sobre la tarjeta de red del guest (red user-mode). Es
  todo lo que el guest emite y recibe.
- Juan José inició sesión y tecleó los comandos en la VM. Claude Code tomó las capturas
  de pantalla por el monitor de QEMU. Nadie dio contraseñas a Claude Code.

## Ventanas de captura (UTC)

| Ventana | Intervalo | Qué pasa | Paquetes |
|---|---|---|---|
| 1 — arranque | 14:29:40 → 14:31:46 (126 s) | Arranque sin teclear. El TPM abre el disco sin pedir contraseña; a los ~21 s, pantalla de inicio de sesión de lightdm (sin entrar solo, D14) | 2 |
| Sesión | 14:31:46 → 14:36:44 | Juan José inicia sesión y ejecuta los comandos de abajo | 0 |
| 2 — reposo | 14:36:44 → 14:38:50 (126 s) | Sesión abierta, sin tocar nada | 1 (entrante) |

Los 3 paquetes:

```
14:29:41.594866 IP6 :: > ff02::1:ff12:3456: ICMP6, multicast listener report
14:29:42.294830 IP6 :: > ff02::1:ff12:3456: ICMP6, neighbor solicitation, who has fe80::5054:ff:fe12:3456
14:37:25.645029 IP6 fe80::2 > ff02::1: ICMP6, router advertisement
```

Los dos primeros son la detección de dirección duplicada de IPv6 al levantar la interfaz
(link-local, no salen del enlace). El tercero lo **envía** QEMU (`fe80::2`, el lado del
host en la red user-mode) hacia el guest; el guest no responde.

Criterio de `verify-hermetismo-in-qemu.sh`:

| Medida | Valor |
|---|---|
| DNS (puerto 53) | 0 |
| NTP (puerto 123) | 0 |
| HTTP/HTTPS (80/443) | 0 |
| SYN TCP salientes | 0 |
| **Paquetes sospechosos** | **0** |

Observación: el guest no pidió DHCP en todo el tiempo de captura.

## Dentro del sistema (lo tecleó Juan José; captura de pantalla)

| Comando | Resultado |
|---|---|
| `ss -tulpn` | Tabla vacía: **0 sockets TCP/UDP** escuchando ni ligados (ni siquiera en loopback) |
| `apt-cache rdepends --installed libcurl4` | Solo `libtss2-fapi1` (lo esperado según ADR-008) |
| `sudo grep -l libcurl /proc/*/maps` | Sin salida: **ningún proceso** tiene `libcurl` cargada |

## Veredicto

**HERMETISMO OK:** 0 paquetes sospechosos y 0 listeners de red, al arrancar, al iniciar
sesión y en reposo. `libcurl4` está en el disco pero nada la carga: con `nimbo-tpm-setup`
el sistema sigue igual de callado.

## Artefactos (no versionados)

En `repro/out/hermetismo-post-tpm-20261110/` (ignorado por git):

- `post-tpm.pcap` — SHA-256 `5cc45c3c83785330d95d01d3e00f7f7125d63a50cc13ab1b87db6809f1f614ad`
- `s1-arranque.png` (pantalla de inicio de sesión a los 21 s), `s2-fin-ventana1.png`,
  `s3-terminal.png` (salida de los comandos), `s4-fin-reposo.png`
- `t0`…`t3` — marcas de tiempo (epoch UTC) de las ventanas

Las capturas no muestran contraseñas: `sudo` no hace eco.

## Incidencia del arnés

El primer intento falló antes de arrancar la VM: la ruta del socket del monitor
(`NIMBO_QEMU_MONITOR`) pasaba de 108 bytes, el límite de los sockets UNIX. Quedó un
`swtpm` huérfano, que se cerró a mano antes de repetir. Con el socket en
`$XDG_RUNTIME_DIR` funcionó. No afecta a la medición. Mejora posible: que el arnés
compruebe la longitud, como ya hace con el socket de swtpm.
