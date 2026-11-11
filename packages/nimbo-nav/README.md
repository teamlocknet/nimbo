# packages/nimbo-nav — navegación segura

Implementa el [ADR-012](../../docs/adr/ADR-012-navegacion-segura-tor.md): RF-NAV-01
(navegador endurecido) y RF-NAV-02 (Tor con detección de fugas).

**Dueño:** Emmanuel (`@Cardozo-Mosquera`)

## Qué instala el paquete `nimbo-nav`

| Fichero | Destino | Para qué |
|---|---|---|
| `config/firefox/policies.json` | `/etc/firefox/policies/` | Políticas bloqueadas: sin telemetría, estudios, Pocket, cuentas, DoH, portal cautivo, sugerencias ni Safe Browsing (RF-NAV-01) |
| `config/firefox/nimbo-nav.js` | `/usr/lib/firefox-esr/defaults/pref/` | Preferencias que las políticas no cubren (telemetría de `toolkit.*`, Normandy, actualizaciones de extensiones y de complementos multimedia, Remote Settings) |
| `config/tor/tor-user.js` | `/usr/share/nimbo-nav/` | Perfil Tor: SOCKS5 `127.0.0.1:9050`, DNS remoto, sin caída a directo, WebRTC e IPv6 apagados |
| `config/nftables/nimbo-tor.nft` | `/usr/share/nimbo-nav/` | Tabla del modo Tor: solo sale `debian-tor`; lo demás se cuenta como fuga y se descarta |
| `config/systemd/nimbo-modo-tor.service` | `/usr/lib/systemd/system/` | El modo Tor: tabla → tor → vigilante; al parar, al revés. Sin `[Install]`: nunca arranca sola |
| `config/systemd/nimbo-leakcheck.service` | `/usr/lib/systemd/system/` | Vigilante de fugas, solo mientras el modo Tor está activo; `Restart=on-failure` |
| `config/applications/nimbo-navegar-tor.desktop` | `/usr/share/applications/` | Lanzador "Navegar por Tor" |
| `src/nimbo_nav/` | Python 3.11, solo biblioteca estándar | `nimbo-tor`, `nimbo-leakcheck`, `nimbo-navegar-tor` |

Al instalarse por primera vez, el `postinst` **deshabilita y para** el servicio de `tor`
que deja el paquete de Debian: tor no arranca solo (RNF-01).

## Uso

```
firefox-esr                 # navegador normal, endurecido (sin Tor)
sudo nimbo-red on           # levanta la red por cable (ADR-019); sin red no hay Tor
nimbo-tor on                # arranca nimbo-modo-tor.service (systemd pide autorización)
nimbo-navegar-tor           # Firefox con el perfil Tor; avisa si hay fuga o si el vigilante falla
sudo nimbo-leakcheck        # 0 = sin fugas · 1 = FUGA · 2 = modo apagado · 3 = no se pudo comprobar
nimbo-tor off               # para el modo Tor (vigilante -> tor -> tabla)
sudo nimbo-red off          # suelta la red
```

Mientras el modo Tor está activo, **solo tor sale a la red** (también el navegador normal
queda sin red). Límite declarado (ADR-012): *"evita fugas de red; no protege frente a la
huella del navegador"*. El perfil Tor lleva `resistFingerprinting` y `letterboxing`, que
reducen la brecha con Tor Browser pero no la cierran, y el **OCSP apagado** (no consulta la
revocación de certificados, para no hacer peticiones fuera de la navegación).

## Pruebas

**Unitarias** (sin red ni root; Python 3.11 + pytest 7.2, como en bookworm):

```
cd packages/nimbo-nav && python3 -m pytest -q
```

**En una VM Debian 12 con red** (VirtualBox/VMware, 2 GiB, snapshot antes de empezar):

```
sudo bash packages/nimbo-nav/pruebas/preparar-vm.sh          # instala dependencias, construye e instala el .deb
bash packages/nimbo-nav/pruebas/prueba-reposo-navegador.sh   # RF-NAV-01: 120 s en reposo, 0 sospechosos
bash packages/nimbo-nav/pruebas/prueba-fugas-tor.sh          # RF-NAV-02: 0 DNS y 0 fuera del túnel + prueba negativa
```

Rojo primero para RF-NAV-01: ejecuta `prueba-reposo-navegador.sh sin-nimbo-nav` **antes**
de `preparar-vm.sh` (solo `apt install firefox-esr tcpdump`) para ver las conexiones de un
Firefox de serie. Cada prueba deja `informe.md` y el pcap en una carpeta del directorio actual.

**Construir el .deb con Docker** (como `nimbo-audit`, ADR-010): `sudo bash packages/nimbo-nav/build-deb.sh`.

## Pendiente de medir (ADR-012)

- Que `firefox-esr` 140 lea `/etc/firefox/policies/policies.json` (`about:policies` sin errores).
- Que `services.settings.server = "data:,"` no rompa el navegador.
- Que `tor@default.service` sea la unidad que arranca el proceso en tor 0.4.9 de bookworm.
- Cuánto crece la ISO al integrar (`firefox-esr` ocupa ~272 MiB instalado).
