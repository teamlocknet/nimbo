# Plan de integración a la ISO — nimbo-nav y hardening 3B.2 (checkpoint, E8)

**Estado:** propuesta para el checkpoint de Juan José. **No está aplicada.** Todos los
cambios tocan ficheros del núcleo (`iso/live-build/`, `.github/workflows/`) y cambian el
SHA de la ISO; por eso los aplica o aprueba Juan José, siguiendo el mismo camino que el
PR-B de `nimbo-audit` (#42).

## 1. Ficheros existentes que hay que modificar

| Fichero | Cambio | Por qué |
|---|---|---|
| `iso/live-build/build-in-container.sh` | Montar `packages/nimbo-nav` como `/src/nimbo-nav` (igual que `AUDIT_SOURCE`), construirlo con `dpkg-buildpackage -us -uc -b` y copiar **los dos** `.deb` a `config/packages.chroot/`. Hoy el script exige exactamente un `.deb` (`[ "$#" -eq 1 ]`, `Package = nimbo-audit`): hay que admitir la lista `nimbo-audit nimbo-nav` | Es la única vía por la que entra un paquete propio a la ISO |
| `.github/workflows/build-iso.yml` y `repro-verify.yml` | Añadir `packages/nimbo-nav/**` y `security/hardening/3b2/**` a los filtros `paths` | Si no, un cambio en estos módulos no recompila la ISO ni pasa la compuerta MATCH |
| `.github/workflows/ci.yml` | Job de pruebas de `nimbo-nav` con el Python 3.11 de bookworm (`python3 -m pytest` en `packages/nimbo-nav`) y `bash security/hardening/3b2/pruebas/test-verify-hardening.sh`; añadir `packages/nimbo-nav` al job `estructura` | Rojo/verde en CI, no solo en local |

## 2. Ficheros nuevos en la receta

| Fichero | Contenido |
|---|---|
| `config/package-lists/nav.list.chroot` | `nimbo-nav` (arrastra `firefox-esr`, `tor`, `nftables`, `libnotify-bin` desde el snapshot) |
| `config/hooks/normal/0185-nimbo-nav.hook.chroot` | Como 0180: `apt-mark manual nimbo-nav`; comprobar que `tor@default.service` **no** está habilitado; que existen `/etc/firefox/policies/policies.json` y `/usr/share/nimbo-nav/nimbo-tor.nft`; `nimbo-tor --help`. Debe ir **antes** de 0200 (pool local) |
| `config/includes.chroot/etc/sysctl.d/99-nimbo-hardening.conf` | Copia de `security/hardening/3b2/sysctl/` |
| `config/includes.chroot/usr/share/nimbo/hardening/99-nimbo-hardening.conf` | Lista de referencia del verificador |
| `config/includes.chroot/etc/security/faillock.conf` y `usr/share/pam-configs/nimbo-faillock*` | Copias de `security/hardening/3b2/pam/` |
| `config/includes.chroot/usr/lib/nimbo/verify-hardening` | `security/hardening/3b2/verify-hardening.sh` (modo 0755) |
| `config/hooks/normal/0170-nimbo-hardening-3b2.hook.chroot` | `pam-auth-update --package --enable nimbo-faillock nimbo-faillock-preauth` y comprobar que `common-auth` lleva `pam_faillock` |

Alternativa más limpia (a decidir): empaquetar el hardening como un `.deb` `nimbo-hardening`
en lugar de `includes.chroot`, para que se instale igual en el sistema instalado.

## 3. Verificación tras integrar (la corre Juan José o la CI)

1. CI: pruebas de `nimbo-nav` y del verificador en verde; **MATCH ×2**.
2. QEMU, ISO live: `verify-hermetismo-in-qemu.sh` → 0 sospechosos, 0 listeners (**tor apagado**).
3. QEMU: `measure-ram-in-qemu.sh` → < 500 MB en reposo, en live e instalado.
4. QEMU, live e instalado: `sudo /usr/lib/nimbo/verify-hardening` → `VEREDICTO: OK — 0 fallos`
   (RF-CORE-04 CA-1/CA-2), e inicio de sesión correcto.
5. Medir cuánto crece la ISO (hoy 459 MiB; `firefox-esr` ocupa unos 272 MiB instalado).
6. VM con red: `pruebas/prueba-reposo-navegador.sh` y `pruebas/prueba-fugas-tor.sh`.

## 4. Riesgos a decidir en el checkpoint

- **Tamaño de la ISO** y tiempo de compilación por `firefox-esr`.
- El hook 0200 (pool local) y 0210 (auditoría de backports) deben seguir limpios: ningún
  paquete nuevo debe venir de backports.
- La red de la ISO (sin NetworkManager): cómo se conecta el usuario para navegar (ADR-012, abierto).
