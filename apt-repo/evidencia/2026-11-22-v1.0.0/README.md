# Validación APT de v1.0.0 en Bookworm limpio

Ejecución real del **22-nov-2026**. [Resultados y procedimiento](RESULTADOS.md).
37/37 comprobaciones correctas; cuatro tests APT con resultado OK.

Publicación: [run 44824465730, intento 1](https://github.com/teamlocknet/nimbo/actions/runs/44824465730).
Paquetes del tag v1.0.0: 94f9b8fec60938baccae984f891cc3ac6960e109.
Cliente: VM Debian 12 Bookworm limpia, distinta del host y de la ISO nimbo.

BASELINE.json recoge el estado previo sin módulos, fuente ni clave de nimbo en
los llaveros APT. COMPROBACIONES.json enlaza los resultados medidos. Los archivos
*.json de cada comando conservan argv, fechas y código de salida; *.stdout.log y
*.stderr.log conservan las salidas. SHA256SUMS cubre toda esta carpeta.

La preparación del 18-nov queda en ../2026-11-18-v1.0.0/ y no se presenta como
validación final. Este PR aporta la validación; Juan José decide la aceptación
de RF-DIST-01 y su merge.
