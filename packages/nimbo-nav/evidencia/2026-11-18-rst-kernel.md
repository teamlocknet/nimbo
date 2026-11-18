# Evidencia — RST del kernel de una conexión de tor contados como "fuga" (18-nov-2026, #101)

**Quién:** Emmanuel, con Claude Code manejando la VM (la contraseña de `sudo` la tecleó
Emmanuel). **Origen:** ensayo de la demo de Juan José (ISO `732e45fd…`): `nimbo-fuga … DPT=8080
RST` en el journal; en el pcap del hipervisor, la conexión de tor con su relé de entrada; no salió
nada.

## Entorno

- ISO de `main` `eb3bc36` (`b0df8d62…`) instalada en VirtualBox (`nimbo-iso-nav`), red NAT con
  `sudo nimbo-red on`. Tabla instalada: `nimbo-tor.nft` de `main` (sha256 `860ad2cebb31174d…`).
- Tabla propuesta en #101 (sha256 `d975f862c9e09f0f…`, la del PR byte a byte): tor marca sus
  conexiones (`meta skuid "debian-tor" ct mark set 0x6e74 accept`) y se aceptan los paquetes de
  una conexión marcada (`ct mark 0x6e74 accept`).
- Prueba: `pruebas/prueba-rst-kernel.sh`. Activa el modo Tor y espera a `Bootstrapped 100%`, mata
  tor con `SIGKILL`, espera 30 s, mira el contador `fugas` y las líneas `nimbo-fuga`, y hace una
  **prueba negativa**: una conexión directa de `nobody` a `1.1.1.1:443`. Al final deja la tabla
  instalada como estaba. El script y la tabla entraron en la VM por el teclado virtual, con el
  SHA-256 comprobado.

## Resultados

| Pasada | `nft -c` | Fugas al matar tor | Líneas `nimbo-fuga` | Prueba negativa | Veredicto |
|---|---|---|---|---|---|
| Tabla actual ([captura](2026-11-18-rst-kernel/1-rojo-tabla-actual.png)) | — | **0 → 12 (+12)** | RST de `10.0.2.15` a los relés `217.160.126.155:443` y `57.131.130.172:9100` | +2 | **ROJO**: el contador sube sin fuga |
| Tabla con marca ([captura](2026-11-18-rst-kernel/2-verde-tabla-con-marca.png)) | sintaxis OK | **0 → 0 (+0)** | ninguna | **+2** | **VERDE** |

Después de cada pasada, la tabla instalada volvió a `860ad2cebb31174d…`.

**Conclusión:** los RST que el kernel manda sin proceso dueño al cerrarse las conexiones de tor
contaban como fuga. Con la marca de conntrack dejan de contar, y una conexión directa de otro
usuario se sigue detectando.

## Límites

- Se provocó matando tor (`SIGKILL`). En la demo el RST salió en un cierre normal de conexión: el
  mecanismo es el mismo (paquete del kernel sin dueño en una conexión de tor), pero ese caso no se
  reprodujo tal cual.
- Los **ICMP de error** del kernel (la observación de #84) **no se midieron**. Deberían heredar la
  marca de su conexión, pero falta comprobarlo.
- Cambiar la tabla es **checkpoint de Juan José**.
