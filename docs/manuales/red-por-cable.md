# Manual — Conectar el equipo a la red (`nimbo-red`)

**Para:** quien usa un equipo nimbo instalado. **Requisitos:** RNF-01, RNF-03, RNF-06.
**Diseño:** [ADR-019](../adr/ADR-019-red-a-demanda.md). **Detalle técnico:**
[`packages/nimbo-red`](../../packages/nimbo-red/README.md).

nimbo **arranca sin red**: ninguna tarjeta está configurada, así que en reposo el equipo no
habla con nadie. Cuando necesitas red (navegar por Tor, la red privada del equipo), la
levantas tú y la apagas al terminar.

| Quiero… | Comando |
|---|---|
| Ver si hay red | `nimbo-red estado` |
| Levantar la red por cable | `sudo nimbo-red on` (con varias tarjetas: `sudo nimbo-red on <tarjeta>`) |
| Apagarla | `sudo nimbo-red off` |

Lo que responde (medido en la ISO instalada, 16-nov):

```
$ nimbo-red estado
nimbo-red: sin red (apagada)
$ sudo nimbo-red on
nimbo-red: red activa en enp0s3. Para apagarla: sudo nimbo-red off
$ sudo nimbo-red off
nimbo-red: enp0s3 apagada. El equipo queda sin red.
```

## Bueno saber

- **Solo cable.** El Wi-Fi no está soportado en esta versión: con una tarjeta Wi-Fi,
  `nimbo-red` se niega.
- Pide la dirección por DHCP y espera **30 s como máximo**. Si no llega, apaga la tarjeta y
  lo dice: revisa el cable o el router.
- **Al reiniciar, el equipo vuelve a quedar sin red.** No se guarda ninguna configuración.
- En el **modo live** (USB sin instalar) la red sí arranca levantada; `nimbo-red estado` lo
  indica y `sudo nimbo-red off` la apaga igual.
- Códigos de salida: `0` bien · `1` error (sin cable, sin DHCP…) · `2` falta `sudo`.

## Con los otros módulos

- **Modo Tor:** primero `sudo nimbo-red on`, después `sudo nimbo-tor on`
  ([navegación segura](navegacion-segura.md)). Al terminar, al revés.
- **Red privada del equipo:** primero `sudo nimbo-red on`, después `sudo nimbo-net join`
  ([red privada](red-privada-equipo.md)).
- **Actualizar** no necesita red: se hace por USB ([actualización](actualizacion-sin-conexion.md)).
