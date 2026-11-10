# ADR-019 — Red por cable solo a demanda (`nimbo-red`)

**Estado:** Aceptado (10-nov, Juan José) · **Dueño:** Juan José (núcleo) · **Origen:**
respuesta 3 a las preguntas del ADR-012 (PR #45)

## Contexto

- La ISO trae `ifupdown`, `isc-dhcp-client` e `iproute2`, pero **ninguna interfaz
  configurada** ni NetworkManager. Por eso el sistema no pide DHCP: medido el 10-nov, en
  ~9 minutos tras `nimbo-tpm-setup` solo hubo 3 paquetes IPv6 del propio enlace (PR #50).
- Hay módulos que sí necesitan red: el modo Tor (ADR-012, `nimbo-nav`) y la red privada
  del equipo (`nimbo-net`, RF-RED-01, Alejandro). El manual del Design Partner (#48) pide
  visitar una web por Tor y hoy no hay forma de levantar la red.
- Restricciones: hermetismo en reposo (RNF-01: 0 sospechosos, 0 listeners), RAM < 500 MB,
  todo de bookworm `main`, nada que arranque solo.

## Opciones

| Opción | A favor | En contra |
|---|---|---|
| A. `allow-hotplug` + DHCP en `/etc/network/interfaces` | Red automática al enchufar el cable | El equipo sale a la red solo: rompe "offline por defecto" y el hermetismo medido |
| B. NetworkManager | Interfaz gráfica, Wi-Fi | Paquete nuevo y demonio en reposo, comprobación de conectividad que hay que apagar, más RAM y superficie |
| **C. `nimbo-red on/off`: `ip` + `dhclient` a mano, sin persistencia** | Nada nuevo en la ISO; en reposo no cambia nada; la red existe solo mientras alguien la pide | Hay que teclear un comando con `sudo`; solo cable |

## Decisión

**C.** `nimbo-red` (`packages/nimbo-red/`, Python, `.deb`):

- `sudo nimbo-red on [interfaz]`: elige la **única** interfaz por cable (`en*`/`eth*`, sin
  `wireless/` ni `phy80211` en `/sys/class/net`). Con varias, **exige indicar cuál**. La
  levanta y pide **una** concesión DHCP (`dhclient -1`, 30 s como máximo). Si no llega,
  baja la interfaz y lo dice.
- `sudo nimbo-red off`: suelta la concesión (`dhclient -r`), borra las direcciones y baja la
  interfaz. Recuerda cuál levantó `on`.
- `nimbo-red estado`: sin privilegios.
- La concesión, el PID y la interfaz activa viven en `/run/nimbo-red/`. **No** escribe en
  `/etc/network/interfaces` ni deja servicios: al reiniciar, el equipo vuelve a quedar
  sin red.
- **Wi-Fi fuera de v1** (no hay `wpasupplicant`): con una interfaz Wi-Fi se niega.

## Cómo se verifica

| Qué | Prueba | Pasa si |
|---|---|---|
| Lógica | 16 tests con un ejecutor falso y un `/sys/class/net` falso (rojo primero), en CI con el Python de bookworm | Todos en verde |
| En reposo no cambia nada | `verify-hermetismo-in-qemu.sh` con `nimbo-red` en la ISO | 0 sospechosos, 0 listeners |
| `on` solo hace DHCP | QEMU con captura: `nimbo-red on` y 60 s quieto | DHCP (y DNS solo si alguien navega) |
| `off` devuelve el silencio | La misma captura tras `nimbo-red off` | 0 paquetes nuevos del sistema |

## Consecuencias

- **Gana:** el modo Tor y `nimbo-net` tienen un camino de red explícito, y el principio
  "offline por defecto" queda escrito y medible.
- **Paga:** comando con `sudo`. `dhclient-script` reescribe `/etc/resolv.conf` con el DNS de
  la concesión, y ese fichero se queda tras `off` hasta el siguiente arranque o concesión.
  Sin red no se usa, pero conviene saberlo.
- **`nimbo-tor` y `nimbo-net`** deben dar por hecho que la red la levanta `nimbo-red`, y no
  configurarla por su cuenta.
- **Integración en la ISO:** PR aparte, con checkpoint de receta y compuerta MATCH ×2.

## Fecha

2026-11-10
