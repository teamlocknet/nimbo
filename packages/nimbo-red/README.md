# nimbo-red — red por cable solo a demanda

**Diseño:** [ADR-019](../../docs/adr/ADR-019-red-a-demanda.md) · **Dueño:** Juan José (núcleo).

nimbo arranca **sin red**: ninguna interfaz está configurada, así que en reposo no hay
DHCP ni ninguna otra conexión (hermetismo, RNF-01). Cuando hace falta red —navegar por Tor,
la red privada del equipo— se pide a mano:

| Quiero… | Comando |
|---|---|
| Levantar la red por cable | `sudo nimbo-red on` (con varias interfaces: `sudo nimbo-red on <interfaz>`) |
| Apagarla | `sudo nimbo-red off` |
| Ver el estado | `nimbo-red estado` |

- Pide **una** concesión DHCP, con 30 s como máximo. Si no llega, baja la interfaz y lo dice.
- No escribe en `/etc/network/interfaces` ni deja servicios: la concesión y el PID viven en
  `/run/nimbo-red/`. **Al reiniciar, el equipo vuelve a quedar sin red.**
- **Solo cable.** Con una interfaz Wi-Fi se niega: Wi-Fi está fuera de v1 (no hay
  `wpasupplicant`).
- **En el live** la red sí arranca levantada: `live-boot` deja la interfaz en `ifupdown`
  (`ifup@<interfaz>`) con su propio `dhclient`. `estado` mira las direcciones reales del
  kernel y lo dice ("levantada fuera de nimbo-red"); `off` hace `ifdown` cuando la interfaz
  es de `ifupdown`, para que ese `dhclient` suelte la concesión y se pare.
- Códigos de salida: `0` OK · `1` error · `2` sin privilegios.

## Tests

```
PYTHONPATH=src python3 -m pytest          # local
CONTAINER_ENGINE=docker ci/test-modulo-en-bookworm.sh packages/nimbo-red   # como en CI
```

En la ISO desde #81 ([ADR-020](../../docs/adr/ADR-020-modulos-en-la-iso.md)).
