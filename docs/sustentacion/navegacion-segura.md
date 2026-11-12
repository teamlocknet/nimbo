# Navegación segura (`nimbo-nav`) — RF-NAV-01 y RF-NAV-02

## Qué hace

- **Firefox que no habla solo.** `firefox-esr` de Debian con políticas y preferencias bloqueadas:
  al abrirlo y dejarlo quieto, **no se conecta a nada**.
- **Modo Tor a petición.** `nimbo-tor on` arranca una unidad systemd que primero carga un
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
| Lógica | 52 pruebas unitarias escritas antes que el código, en CI con el Python de bookworm |

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

## Lo que falta

Repetir las dos pruebas sobre **la ISO integrada**. Hoy la ISO **no lleva Firefox**: entrará
al integrar `nimbo-nav`, en la versión del snapshot (`firefox-esr` 140.14). Las mediciones de
arriba se hicieron con la 153.6 de Debian actual.

*Evidencia:* `packages/nimbo-nav/evidencia/2026-11-10-vm-rf-nav-01.md` · *Diseño:* ADR-012 ·
*Manual:* `docs/manuales/navegacion-segura.md`
