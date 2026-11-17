# Navegación segura (`nimbo-nav`) — RF-NAV-01 y RF-NAV-02

## Qué hace

- **Firefox que no habla solo.** `firefox-esr` de Debian con políticas y preferencias bloqueadas:
  al abrirlo y dejarlo quieto, **no se conecta a nada**.
- **Modo Tor a petición.** `sudo nimbo-tor on` arranca una unidad systemd que primero carga un
  cortafuegos (solo puede salir el proceso `tor`) y después arranca Tor. Si algo intenta salir
  por fuera, se bloquea y se cuenta.
- **Aviso de fugas.** `nimbo-leakcheck` vigila ese contador y las conexiones abiertas; el
  navegador avisa también si el vigilante falla (nunca da por "limpio" lo que no sabe).

**Límite que se declara tal cual:** *evita fugas de red; no protege frente a la huella del
navegador* (no es Tor Browser).

## Cómo se prueba

| Requisito | Prueba |
|---|---|
| RF-NAV-01 | Firefox con perfil nuevo, 120 s quieto, captura de todo el tráfico de la máquina |
| RF-NAV-02 | Modo Tor cargando 3 sitios con captura; después, **prueba negativa**: un `curl` directo a propósito que el sistema debe detectar |
| Lógica | Pruebas unitarias escritas antes que el código (rojo → verde), en CI con el Python de bookworm |
| Sobre la ISO | La captura la hace el **hipervisor** (VirtualBox), no el sistema probado: no se le instala nada; `pruebas/analizar_pcap.py` aplica los mismos criterios |

## Qué se midió (VM Debian 12, 10 y 11-nov)

| | Paquetes sospechosos en 120 s |
|---|---|
| Firefox de serie (rojo) | **38 011** (154 consultas DNS) |
| Con `nimbo-nav` tal como se escribió | 32 159 |
| Con las rutas de Debian corregidas y Remote Settings apagado | 1 269 |
| **Versión final** (también en una sesión nueva, sin pasos a mano) | **0** |
| Control: lo mismo + una consulta DNS hecha a propósito | 2 → **la captura sí detecta** |

RF-NAV-02: **0 DNS y 0 paquetes fuera del túnel** (3 796 capturados); la fuga provocada se
bloqueó y `nimbo-leakcheck` la detectó.

## Qué se midió sobre la ISO instalada (16-nov)

ISO de `main` `eb3bc36` (`b0df8d62…`, MATCH ×2), instalada con Calamares cifrado; `firefox-esr`
140.14 del snapshot.

| Prueba | Resultado |
|---|---|
| RF-NAV-01: red arriba, sin Firefox (control) | 0 sospechosos |
| RF-NAV-01: Firefox, perfil nuevo, 120 s quieto | **0 sospechosos** |
| Control positivo: una consulta DNS a propósito | detectada |
| HU-07 CA-2: `about:policies` | telemetría, estudios, informes y actualizaciones: desactivados, sin errores |
| RNF-01 con `nimbo-nav` instalado | **0 puertos escuchando** en reposo |
| RF-NAV-02: navegar por Tor (check.torproject.org, example.com, debian.org) | "Congratulations… configured to use Tor"; **7 105 paquetes, 0 DNS, 0 fuera del túnel** |
| Fuga provocada | bloqueada; `nimbo-leakcheck` → FUGA detectada (código 1) |
| HU-08 CA-3: el aviso **llega al usuario** | ❌ **no**: la ISO no trae servicio de notificaciones (hallazgo 7) |

## Hallazgos (lo que solo salió en un Debian real)

1. **Firefox de Debian ignoraba nuestras preferencias:** las lee de `/etc/firefox-esr/`, no de
   la carpeta estándar. Medido con `about:config`.
2. **Remote Settings no se apaga en Firefox "release"** salvo con una variable de entorno
   (`MOZ_REMOTE_SETTINGS_DEVTOOLS=1`); era la descarga de decenas de MB.
3. **La última conexión eran los fondos de la nueva pestaña:** Firefox la precarga aunque abra en
   blanco. Identificado con el registro HTTP interno (`MOZ_LOG`).
4. **Falso positivo de DHCP** en el detector de fugas (la tabla lo permitía; el detector no).
5. **Fallo cerrado, provocado a propósito en la VM** (`pruebas/prueba-arranque-fallido.sh`,
   11-nov): con tor sin poder arrancar, `nimbo-tor on` falla, la unidad queda `failed`,
   `ExecStopPost` **borra la tabla** (`nft` confirma que ya no existe), `nimbo-tor estado` dice
   "falló" y `nimbo-tor off` **no** dice "red restaurada". `nimbo-tor off` decide por el estado
   de la unidad; que la tabla no quede la confirmó la prueba con `nft`.

6. **La ISO no trae polkit** (ISO, 16-nov): `nimbo-tor on` sin `sudo` daba "Access denied".
   El diseño contaba con que "systemd pide la contraseña". Ahora `nimbo-tor` dice "Usa: sudo
   nimbo-tor on" y los manuales usan `sudo` (#92).
7. **La ISO no trae servicio de notificaciones** (ISO, 16-nov): `notify-send` falla, así que el
   aviso de fuga del navegador no se ve, aunque la protección y la detección sí funcionan. Salió
   al revisar la evidencia contra cada criterio de HU-08, no al medir: el veredicto "pasa" se
   corrigió. Propuesta: `xfce4-notifyd` (#96, checkpoint de Juan José).
8. **La herramienta de medición también se prueba:** el analizador de capturas no seguía las
   cabeceras de extensión IPv6, por donde podría colarse una fuga sin contarse. Se vio al leer
   la primera captura real y se corrigió con su prueba antes de medir RF-NAV-02.

## Lo que falta

HU-08 CA-3 en una ISO con `xfce4-notifyd` (cuando Juan José acepte #96): provocar una fuga con
el navegador Tor abierto y ver el aviso en pantalla.

*Evidencia:* `packages/nimbo-nav/evidencia/2026-11-10-vm-rf-nav-01.md` (VM Debian) y
`packages/nimbo-nav/evidencia/2026-11-16-iso-rf-nav.md` (ISO instalada) · *Diseño:* ADR-012 ·
*Manual:* `docs/manuales/navegacion-segura.md`
