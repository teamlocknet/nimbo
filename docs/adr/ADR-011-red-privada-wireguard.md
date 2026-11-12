# ADR-011 — Red privada del equipo con WireGuard a demanda

**Estado:** Aceptado por Juan José tras revisar las pruebas de dos VMs y las
aclaraciones de #71 (commit 8e121e4). La aceptación del diseño no cierra
la validación pendiente sobre la ISO integrada.
**Responsable:** Alejandro. **Requisitos:** RF-RED-01 / HU-09; RNF-01 y RNF-03.

## Contexto

Dos equipos deben conectarse mediante un túnel cifrado con un solo
`nimbo-net join` por equipo. La preparación de claves y perfiles se declara como
un paso previo separado; no forma parte del comando de activación.
El alcance aprobado es WireGuard directo, dos pares con endpoints alcanzables.
No se promete atravesar CGNAT, UDP bloqueado ni NAT arbitrario.

La red física pertenece a `nimbo-red` (ADR-019). El modo Tor (ADR-012) y la VPN
son mutuamente excluyentes en v1. El hardening (ADR-014) fija `rp_filter=1`.
Nada relacionado con la VPN debe arrancar automáticamente ni generar actividad
antes de join. Las claves privadas nunca se comparten ni se versionan.

## Alternativas consideradas

| Alternativa | Evaluación para este alcance |
|---|---|
| WireGuard directo con wg e ip | Elegida en el checkpoint: pares preparados, endpoints alcanzables y ciclo de vida explícito |
| wg-quick con perfiles arbitrarios | Se evita aceptar hooks o comandos de shell en perfiles privilegiados |
| Tailscale con coordinación alojada | No se elige para el alcance aprobado; introduciría otra infraestructura que evaluar |
| Cliente Tailscale con Headscale propio | No se elige: operación y disponibilidad de un coordinador adicional fuera del alcance de dos pares preparados |

## Decisión

### Preparación previa, separada de join

Cada equipo genera su propia clave localmente con las herramientas de WireGuard.
La privada permanece en ese equipo, en un directorio root:root 0700 y archivo
0600, fuera del repositorio. Solo se intercambian clave pública, dirección del
par y endpoint, confirmando su origen con la otra persona.

Un perfil local administrado por root declara la clave propia, clave pública del
par, direcciones IPv4 del túnel, IP numérica del endpoint y puerto. Se proponen
`/etc/nimbo-net/perfil.json` y un archivo de clave protegido. No admite hooks ni
comandos, ni enlaces simbólicos o escritura por usuarios ajenos. Antes de usarlo
se validan formato, permisos, rutas y conflictos. La preparación no levanta la
interfaz ni abre el puerto. Las pruebas generan sus propias claves efímeras.

### Activación y limpieza

- `sudo nimbo-net join`: usa un perfil previamente preparado, sin argumentos
  obligatorios. Comprueba la red física disponible mediante el contrato de
  `nimbo-red`; si falta, indica `sudo nimbo-red on` y falla sin activar la VPN.
  No invoca DHCP ni levanta interfaces físicas por su cuenta.
- Se confirma **wg-nimbo** como nombre de interfaz. Coincide con
  `INTERFAZ_NIMBO_NET` y `AssertPathExists=!/sys/class/net/wg-nimbo` de Emmanuel,
  ya presentes en main 8d01002. Una interfaz ajena con ese nombre es un conflicto,
  no un recurso que se pueda borrar o adoptar silenciosamente.
- Se configura con wg e ip mediante listas de argumentos, sin shell. Túnel
  dividido: direcciones/rutas de los pares, sin ruta por defecto, cambios de DNS,
  forwarding ni NAT. IPv4 es el alcance inicial; no se desactiva IPv6 del sistema.
- Join solo informa conexión tras handshake y tráfico de prueba al par con espera
  acotada. Dos equipos que ejecutan join uno después del otro deben disponer de
  una ventana de espera documentada; interfaz creada no significa conectado.
- `nimbo-net status` permite consultar estado sin revelar secretos.
  `sudo nimbo-net leave` retira solo interfaz, rutas y estado creados por nimbo-net.
  No ejecuta `nimbo-red off` ni elimina recursos de otros módulos.
- Fallos y timeout requieren limpiar los recursos propios. Repeticiones de join
  o leave no deben duplicar recursos. Se serializan operaciones del módulo.
- No se instala servicio de arranque ni se activa keepalive persistente por defecto.
  Tras reinicio, el túnel está inactivo; las identidades locales pueden persistir.

### Exclusión mutua con Tor y reglas de red

Join se niega antes de modificar red si existe la tabla `inet nimbo_tor` o si
`nimbo-modo-tor.service` está activo o en transición de arranque/parada. Si no se
puede determinar el estado, falla con diagnóstico; no interpreta un error de
consulta como prueba de que Tor está apagado.

En sentido inverso, nimbo-tor on ya comprueba la existencia de wg-nimbo y la
unidad systemd incorpora la misma barrera. nimbo-net no modifica esos archivos.
La prueba incluye ambos órdenes y activaciones concurrentes: las comprobaciones
por sí solas no acreditan exclusión atómica. Si se observa una carrera, se acuerda
con Emmanuel un mecanismo compartido antes de declarar aceptación; cualquier
cambio a su módulo o a la integración se revisa con sus responsables.

Si hacen falta reglas nftables, se limitan a una tabla propia `inet nimbo_net`;
la limpieza elimina solo esa tabla. **Nunca flush ruleset**, ni borrar o modificar
`nimbo_tor`. No se intenta habilitar la VPN mediante excepciones a la política Tor.
No se agrega una tabla sin una necesidad concreta y su prueba.

### Compatibilidad con hardening

Se mantiene **rp_filter=1**: no se cambian sysctl automáticamente. Con el túnel
arriba se registran los valores efectivos de all, default, interfaz física y
wg-nimbo, las rutas y el resultado bidireccional. Se aplica el hardening vigente
`99-zz-nimbo-hardening.conf`. Si hay un fallo atribuible al filtrado inverso,
se entrega evidencia y se solicita un checkpoint para valorar 2. La prueba de laboratorio registró modo estricto efectivo (1) en ens3 y
wg-nimbo con ese archivo aplicado; debe repetirse en la ISO integrada. Túnel completo fuera de v1.

## Verificación y criterios de aceptación

| Prueba | Pasa si |
|---|---|
| Tests del módulo, rojo antes de implementar | CLI y validación rechazan perfiles inválidos, permisos débiles, conflictos, errores de sistema y timeout sin secretos ni residuos |
| Bookworm anclado | Tests con ci/test-modulo-en-bookworm.sh, dependencias APT acordadas; agregar un job requiere checkpoint |
| Dos VMs/equipos, claves generadas localmente y perfiles preparados | Un join por equipo, handshake y tráfico bidireccional verificables con rp_filter=1 |
| Captura física y captura del túnel | Transporte WireGuard entre endpoints; marcador de prueba visible solo en el túnel, no en claro en la física |
| Tor primero y VPN primero | El segundo modo se niega sin borrar recursos del primero; probar también activación concurrente |
| Antes de join y tras reiniciar | Sin wg-nimbo, socket VPN, servicio ni actividad automática; hermetismo global 0 sospechosos / 0 listeners |
| Leave y fallos | Sin recursos VPN propios; red física y recursos ajenos conservados; rutas por defecto y DNS sin cambios atribuibles a nimbo-net |
| Silencio global tras usar red | Se mide después de nimbo-red off; leave no apaga la red física |

Se registran comandos, códigos de salida y evidencia sin credenciales. Tests con
un ejecutor simulado no sustituyen dos VMs, handshake ni captura real. La
integración en la ISO exige checkpoint y MATCH x2; QEMU y hardware se coordinan
con Juan José. Las pruebas de laboratorio y sus límites están en
[RESULTADOS.md](../../packages/nimbo-net/pruebas/laboratorio/RESULTADOS.md).

**Pendiente obligatorio:** repetir RF-RED-01 sobre la ISO integrada, registrando
su propio SHA-256 completo. Las evidencias de la ISO local de laboratorio no
se heredan como aceptación de la imagen integrada. La integración y sus
compuertas requieren el checkpoint de Juan José.

## Consecuencias

Se obtiene una red cifrada entre pares preparados, sin coordinador ni actividad
VPN al arrancar. Se paga la preparación de perfiles y el requisito de endpoints
alcanzables. No hay descubrimiento automático, relay, CGNAT garantizado, Wi-Fi,
túnel completo ni ejecución simultánea con Tor en v1. No cifra automáticamente
la navegación ni comparte archivos por sí solo.

## Fecha

2026-11-11
