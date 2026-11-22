# Red privada del equipo (`nimbo-net`) — RF-RED-01

**Responsable:** Alejandro.

## Qué hace

- **Une dos equipos en un túnel WireGuard** con un solo `nimbo-net join` en cada uno, tras una
  preparación previa de claves y perfiles.
- **Las claves privadas no salen del equipo.** Solo se intercambian la clave pública, la dirección
  y el punto de conexión.
- **No arranca sola:** en reposo no hay interfaz, puerto ni tráfico.
- **No convive con el modo Tor:** el sistema se niega a activar uno si el otro está activo.

**Límite que se declara tal cual:** WireGuard directo entre dos pares con puntos de conexión
alcanzables. No promete atravesar CGNAT, UDP bloqueado ni NAT arbitrario.

## Cómo se prueba

Dos instalaciones independientes de la ISO integrada, cifradas y con Secure Boot, en una red
privada de QEMU. Un agente de solo lectura hace las comprobaciones y captura el tráfico sin
instalar nada en el sistema.

## Qué se midió (ISO `d114b8e`)

| Medida | Resultado |
|---|---|
| Comprobaciones | **64 de 64** |
| Túnel | Handshake en ambos equipos; 3 de 3 pings, 0 % de pérdida |
| Cifrado en el cable | **0 paquetes** con el marcador en la interfaz física; **12 de 12** en el túnel |
| Endurecimiento con el túnel activo | `verify-hardening` 0 de 44; `rp_filter=1` en modo estricto |
| Tras `leave` | Rutas y DNS como estaban |
| Exclusión con Tor | Se niega en ambos órdenes y en 3 rondas simultáneas |

## Hallazgos

1. **El kernel ignora `alias` en `ip link add`.** Por eso `join` fallaba siempre y dejaba la interfaz
   creada, lo que además bloqueaba el modo Tor. Se corrigió con `ip link set … alias` (#66).
2. **El endurecimiento no rompe la red.** Se midió que el túnel funciona con `rp_filter` estricto,
   en vez de relajarlo por adelantado.
3. **El ICMP de WireGuard parecía una fuga de Tor** en la prueba de exclusión (#84). No salía nada;
   se corrigió la tabla en #104 y se midió de +3 a +0.

## Lo que falta

Nada de RF-RED-01 en máquina virtual. No se ha repetido sobre la ISO exacta de `v1.0.0`, ni en dos
equipos físicos.

*Evidencia:* `packages/nimbo-net/pruebas/laboratorio/RESULTADOS-INTEGRADA.md` · *Diseño:* ADR-011 ·
*Manual:* `docs/manuales/red-privada-equipo.md`
