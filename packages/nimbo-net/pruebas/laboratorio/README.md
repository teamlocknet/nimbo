# Laboratorio temporal de nimbo-net

Instrumentación para VMs live desechables, sin modificar la ISO original.
El agente corre como root solo dentro de cada VM y recibe acciones limitadas por
un segundo puerto serie conectado a un socket Unix local. No usar en producción.

- `agente-vm.py`: prepara paquetes offline, genera la clave privada dentro de cada
  VM, instala perfiles públicos y ejecuta las comprobaciones.
- `control-vm.py`: envía una acción JSON y recibe su resultado.
- El directorio del laboratorio debe tener modo 0700. Las claves privadas no salen
  de la VM ni aparecen en las evidencias. Apagar la VM destruye sus cambios en RAM.
- `tor_prepare` copia el código y las unidades reales de nimbo-nav para probar la
  exclusión. No construye ni valida el paquete Debian de nimbo-nav.
- `race` ejecuta `nimbo-net join` y `nimbo-tor on` simultáneamente. Una serie finita
  de intentos no demuestra la ausencia de todas las carreras posibles.

El montaje del initrd y los paquetes auxiliares del ensayo actual están fuera del
repositorio. Estos scripts todavía no constituyen un lanzador autocontenido.
La integración de WireGuard en la ISO, MATCH ×2, Secure Boot y hermetismo de la
imagen final requieren su checkpoint y comprobaciones independientes.
