# ADR-020 — Módulos propios y hardening 3B.2 dentro de la ISO

**Estado:** Propuesto (12-nov, plan aprobado por Juan José; pasa a Aceptado con la
verificación en QEMU) · **Paso:** integración para la demo de la semana del 16-nov

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
- Riesgos que se miden en QEMU, no en el build: faillock con la sesión live (autologin) y
  con el lanzador del instalador; `rp_filter=1` del sysctl con `nimbo-red`.

## Fecha

2026-11-12
