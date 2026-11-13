# ADR-020 — Módulos propios y hardening 3B.2 dentro de la ISO

**Estado:** Aceptado (12-nov, verificado en QEMU por Juan José:
[evidencia](../../repro/evidencia/2026-11-12-qemu-pr81.md)) · **Paso:** integración para la demo
de la semana del 16-nov

## Contexto

Hasta `03ff84c` la ISO solo llevaba un módulo propio, `nimbo-audit` (#42, ADR-010), y el
build exigía exactamente ese `.deb`. Los demás módulos estaban terminados y probados
**fuera** de la ISO: `nimbo-red` (ADR-019), `nimbo-update-offline` (ADR-013), `nimbo-nav`
(ADR-012), `nimbo-net` (ADR-011) y el hardening 3B.2 (ADR-014). El 10-nov se acordó con
el profesor enseñarlos **integrados en la ISO** la semana del 16-nov.

Cada integración cambia el SHA de la ISO y obliga a repetir MATCH ×2, `verificar-instalado`,
hermetismo y RAM. Para no multiplicar esos ciclos, Juan José aprobó el 12-nov hacerlo en
**dos PR**: (1) `nimbo-red`, `nimbo-update-offline` y 3B.2, que no traen paquetes nuevos de
peso, y (2) `nimbo-nav` y `nimbo-net`, que añaden `firefox-esr`, `tor` y `wireguard-tools`.

## Decisión

1. **Una sola lista** de módulos propios: `config/includes.chroot/usr/share/nimbo/modulos.list`.
   De ella leen `build-in-container.sh` (qué compilar), el hook `0185-nimbo-modulos` y los
   verificadores (`verificar-cli-rootfs.sh` y `verificar-instalado.sh`). Viaja al live y al
   instalado.
2. Cada módulo se compila con `dpkg-buildpackage` en el mismo contenedor anclado,
   con las `Build-Depends` de su `debian/control` (`apt-get build-dep`). Entra en la ISO
   por `config/packages.chroot/` y live-build resuelve sus dependencias con apt: **no**
   hace falta duplicarlas en una lista de paquetes.
3. El hook **0185** exige, por cada módulo: instalado, marcado **manual** (para que el
   `autoremove` de `nimbo-final.sh` no lo quite del instalado), cada orden de `/usr/bin`
   responde a `--help` y **ninguna unidad systemd queda habilitada** (nada arranca solo).
4. **3B.2, opción A (Juan José, 12-nov):** sin paquete propio. `build-in-container.sh` copia
   los ficheros desde `security/hardening/3b2/` (una sola fuente) a
   `config/includes.chroot/`, con permisos explícitos, y el hook **0170** activa los
   perfiles con `pam-auth-update` y comprueba el orden `preauth < pam_unix < authfail` y
   la sección `account`.
5. El pool local (hook 0200) rechaza **cualquier** `nimbo-*`: los módulos viajan
   instalados, nunca como `.deb` en el pool.
6. `build-iso.yml` y `repro-verify.yml` vigilan `packages/<módulo>/**` de cada módulo de
   la lista y `security/hardening/3b2/**`. Lo comprueba `tests/test-modulos-en-receta.sh`
   en `tests-build-scripts`.

## Consecuencias

- Añadir un módulo = una línea en `modulos.list` + su ruta en los dos workflows. El test
  falla si falta alguna.
- La opción A es más rápida que un `.deb nimbo-hardening`, pero `faillock.conf` sobrescribe
  un *conffile* de `libpam-modules`: si una actualización de PAM lo trae cambiado, dpkg
  preguntará. Aceptado para v1; con tiempo se empaqueta.
- Hallazgo al integrar: `nimbo-update-offline` **no compilaba como `.deb`** en el
  contenedor anclado. Sus tests crean claves y `gpg` sin `gpg-agent`
  (`--no-install-recommends`) falla. El job de CI no lo veía porque instala `gnupg`
  completo. Corregido en `Build-Depends`.
- Riesgos medidos en QEMU el 12-nov (ISO `2a6cbaaa…`, MATCH ×2): faillock no rompe el
  autologin del live, el login por consola ni el lanzador del instalador; 5 fallos bloquean y lo
  dicen; un acierto pone el contador a cero; `nimbo-red on/off` funciona con `rp_filter=1`;
  `verify-hardening` 0 fallos en live e instalado.
- Hallazgo al verificar: en el live, `nimbo-red estado` dice "sin red" aunque `live-boot` ya
  levantó la interfaz por DHCP (mensaje engañoso; en el instalado no pasa). Arreglo aparte
  (#82).

## PR-2 — `nimbo-nav` y `nimbo-net` (12-nov)

- `modulos.list` suma `nimbo-nav` y `nimbo-net`. Por dependencias entran del snapshot
  `firefox-esr` **140.14.0esr-1~deb12u1** (de `debian-security`; la versión que deben medir
  RF-NAV-01/02), `tor` 0.4.9.11-0+deb12u1 y `wireguard-tools` 1.0.20210914-1+b1.
- El recorrido genérico de 0185 solo ve las unidades del propio módulo. `tor.service` y
  `tor@default.service` son del paquete `tor` (Debian los deja habilitados; los apaga el
  postinst de `nimbo-nav`) y `wg-nimbo` la crea `nimbo-net join` a mano. Por eso 0185 los
  exige **por nombre**: `tor.service`, `tor@default.service`, `nimbo-modo-tor.service` y
  `nimbo-leakcheck.service` presentes y sin arrancar solos; `wg-nimbo` sin
  `/etc/wireguard/wg-nimbo.conf` ni ningún `wg-quick` habilitado. Los dos verificadores
  comprueban lo mismo, más la versión de `firefox-esr` (si el snapshot cambia, avisa de que
  hay que repetir RF-NAV-01/02).
- **Tamaño:** la ISO pasa de 456 MiB (`main` `4bf30b1`) a **546 MiB** (+90 MiB, casi todo
  `firefox-esr`). Compilación local del 12-nov, `ba4f6fc9…`: hook 0185 OK (`tor.service`
  `disabled`; `tor@default`, `nimbo-modo-tor` y `nimbo-leakcheck` `static`, sin `[Install]`),
  `verificar-cli-en-iso.sh` OK, hermetismo live 0 sospechosos / 0 listeners, RAM live 374 MiB.
- **Hallazgo en el live (12-nov, Juan José):** `tor@default.service` sale `enabled-runtime`
  aunque en el chroot era `static`. Lo enlaza en cada arranque `tor-generator` (del paquete
  `tor`) bajo `/run/systemd/generator/tor.service.wants/` porque existe `/etc/tor/torrc`; en el
  chroot los generadores no corren. Solo arranca si arranca `tor.service`, que está `disabled`:
  en el live, `is-active` = `inactive`. Lo que garantiza que Tor no arranca solo es
  `tor.service` deshabilitado. `verificar-instalado.sh` acepta ese único enlace solo con
  `tor.service` sin habilitar y la unidad inactiva (rojo → verde).

## Fecha

2026-11-12
