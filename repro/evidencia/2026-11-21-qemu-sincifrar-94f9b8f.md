# Evidencia — ISO de `v1.0.0` instalada sin cifrar en QEMU con Secure Boot (2026-11-21)

Cierra el modo "sin cifrar" de RF-CORE-02 sobre la ISO del release. El modo cifrado está en
[`2026-11-20-qemu-instalado-94f9b8f.md`](2026-11-20-qemu-instalado-94f9b8f.md).

| | |
|---|---|
| ISO | `63eeb31a33c4a9d4a6597573a6f567d66b6afbbb207286ae7920197414cc0f10` (`v1.0.0`, commit `94f9b8f`) |
| Arnés | `install-in-qemu.sh --sin-cifrar --secure-boot`, variante `v100final`, disco nuevo |
| Lanzador | "Install nimbo without encryption (advanced)" |
| Horario | 21-nov, instalación y arranque terminados a las 19:39 (-05:00) |

Juan José hizo la instalación y tecleó las contraseñas, que no están en ningún registro. **Vio con
los ojos que el instalador no ofrece ninguna opción de cifrado** y que el sistema llega a la
pantalla de inicio de sesión sin pedir contraseña de disco y sin entrar solo.

## Resultados

`verificar-instalado --sin-cifrar --secure-boot`: **VEREDICTO: OK — 0 fallos**
([informe completo](2026-11-21-qemu-sincifrar-94f9b8f/informe-verificar-instalado.txt)).

| Sección | Resultado |
|---|---|
| 1. Sin cifrado | `crypttab` sin entradas, `/` en ext4 directo sobre `/dev/vda3`, ningún volumen LUKS, sin `cryptsetup-initramfs` |
| 2. Initramfs | Sin scripts de live-boot |
| 2b. Secure Boot | `SecureBoot=1`, `SetupMode=0`; el kernel dice "Secure boot enabled" |
| 3. D14 | Sin autologin |
| 5. Sin restos del instalador | Ni Calamares, ni live-boot, ni sus directorios |
| 6. Idioma, zona y swap | `es_CO.UTF-8`, `America/Bogota`, **sin swap** (en claro filtraría memoria) |
| 7. RAM en reposo | **388 MiB**, menos de 500 MB. Medida a los 58 s de arranque, no a los 90 s que pide el verificador para comparar cifras |
| 8. CLI | `nimbo-audit` 0.1.0-1 |
| 9. Módulos y 3B.2 | Los cinco módulos en las versiones de `v1.0.0`; `verify-hardening` **0 fallos de 44** |

**Hermetismo en la red** (contado con `tcpdump -nr` sobre las capturas):

| Captura | Paquetes | DNS | NTP | Web | SYN |
|---|---|---|---|---|---|
| [`instalacion.pcap`](2026-11-21-qemu-sincifrar-94f9b8f/instalacion.pcap) | 18 | 0 | 0 | 0 | 0 |
| [`instalado.pcap`](2026-11-21-qemu-sincifrar-94f9b8f/instalado.pcap) | 2 | 0 | 0 | 0 | 0 |

El sistema instalado lleva 414 paquetes
([lista](2026-11-21-qemu-sincifrar-94f9b8f/paquetes-instalado.txt)).

## Qué se redactó

UUID de las particiones → `<UUID-REDACTADO>`, y códigos de color de la terminal. No había
credenciales que quitar. Hashes de los ficheros versionados:
[`SHA256SUMS`](2026-11-21-qemu-sincifrar-94f9b8f/SHA256SUMS).

## Lo que no cubre

Hardware real. Este modo deja el disco **sin cifrar a propósito**: es la opción avanzada.
