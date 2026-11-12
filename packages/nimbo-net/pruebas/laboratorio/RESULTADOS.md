# Resultado del laboratorio de red privada

Base del código: main `6821936`. Debian bookworm, kernel `6.1.0-52-amd64`,
dos VMs QEMU/TCG con 1536 MiB cada una. ISO live instrumentada temporalmente;
no es una validación de la integración final ni de Secure Boot.

## Resultados observados

- Ambas VMs: handshake WireGuard y tres pings al par, 0 % de pérdida.
- Alias ignorado en `ip link add`, aplicado en `ip link set`: confirma la corrección.
- `rp_filter`: all=1, default=1, wg-nimbo=1; ens3=0. Se registra el valor por
  interfaz sin afirmar que todos son 1. El túnel funcionó con all=1.
- El patrón realmente emitido por ping aparece en la captura del túnel y no en
  la captura de ens3, en ambas VMs. `resultado-capturas.json` usa ese patrón
  de 15 bytes; la primera comprobación había buscado incorrectamente 16 bytes.
- WireGuard conectado primero: `nimbo-tor on` devuelve 2; Tor queda inactivo.
- Tor activo primero, con tabla inet nimbo_tor: join devuelve 1 sin crear wg-nimbo.
- Tres rondas simultáneas de join y Tor en A: Tor devuelve 0 y join devuelve 1.
  Estado final en A: Tor activo sin wg-nimbo. B agota su espera y limpia su interfaz.
- leave y nimbo-red off completan correctamente. Ambas VMs quedan apagadas.

## Alcance y pendientes

Se usaron el código, unidades y reglas reales de nimbo-nav; sus archivos se
copiaron como instrumentación, sin construir su paquete Debian. Tor 0.4.9.11
se instaló desde el snapshot verificado. El laboratorio bloquea la salida a Internet:
no demuestra bootstrap de Tor, navegación ni ausencia de fugas de su navegador.
Las tres rondas comprueban los resultados observados; no muestrean toda transición
ni demuestran ausencia de todas las carreras posibles.

La preparación de perfiles fue previa; cada VM generó su clave privada localmente.
El intento inicial sin perfil no forma parte de la aceptación; con perfiles preparados
se ejecutó un join por equipo y ambos conectaron. No se guardaron claves privadas.

Juan José debe revisar estas evidencias antes de pasar ADR-011 a Aceptado.
Siguen pendientes la integración oficial en ISO, MATCH ×2 y hermetismo de esa imagen.
Los archivos de evidencia tienen hashes en evidencia/SHA256SUMS.
