# Guías de uso de nimbo

**RNF-06 / HT-06 CA-2:** "dado cada módulo del sistema, cuando reviso la documentación,
entonces cada uno tiene su guía". Empieza por la guía de instalación; las demás, cuando
necesites ese módulo.

| Para… | Módulo | Guía |
|---|---|---|
| Instalar nimbo y probarlo en una jornada | ISO + instalador (Calamares, LUKS2) | [Guía de instalación y uso](guia-design-partner.md) |
| Registrar una auditoría con evidencia verificable | `nimbo-audit` | [Auditoría con evidencia](auditoria-con-evidencia.md) |
| Conectar el equipo a la red (y desconectarlo) | `nimbo-red` | [Red por cable](red-por-cable.md) |
| Navegar sin telemetría y por Tor, con detección de fugas | `nimbo-nav` | [Navegación segura](navegacion-segura.md) |
| Unir dos equipos con un túnel cifrado | `nimbo-net` | [Red privada del equipo](red-privada-equipo.md) |
| Actualizar sin internet, desde una USB | `nimbo-update-offline` | [Actualización sin conexión](actualizacion-sin-conexion.md) |
| Entender y comprobar el endurecimiento (sysctl, bloqueo de cuenta) | hardening 3B.2 | [Endurecimiento 3B.2](endurecimiento-3b2.md) |
| Desbloquear el disco con el TPM (opcional) | `nimbo-tpm-setup` | [Desbloqueo con TPM](desbloqueo-tpm.md) |

Si algo de una guía no funciona o no se entiende, anótalo en el
[formulario de hallazgos](formulario-hallazgos-design-partner.md).

**Reglas comunes**

- nimbo **arranca sin red** y no se conecta solo. La red se pide con `sudo nimbo-red on`.
- Lo que cambia el sistema pide `sudo` (tu contraseña). Ninguna guía te pedirá que compartas
  una contraseña o una clave privada con nadie.
- Todo funciona sin internet salvo lo que, por definición, la necesita (Tor, la red del equipo).
