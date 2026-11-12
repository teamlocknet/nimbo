# ADR-011 ? Red privada del equipo con WireGuard a demanda

**Estado:** Propuesto para revision del contrato; alcance aprobado por Juan Jose el
10-nov. Implementacion y pruebas de aceptacion pendientes.
**Responsable:** Alejandro. **Requisitos:** RF-RED-01 / HU-09; RNF-01 y RNF-03.

## Contexto

Dos equipos deben conectarse mediante un tunel cifrado con un solo
`nimbo-net join` por equipo. La preparacion de claves y perfiles se declara como
un paso previo separado; no forma parte del comando de activacion.
El alcance aprobado es WireGuard directo, dos pares con endpoints alcanzables.
No se promete atravesar CGNAT, UDP bloqueado ni NAT arbitrario.

La red fisica pertenece a `nimbo-red` (ADR-019). El modo Tor (ADR-012) y la VPN
son mutuamente excluyentes en v1. El hardening (ADR-014) fija `rp_filter=1`.
Nada relacionado con la VPN debe arrancar automaticamente ni generar actividad
antes de join. Las claves privadas nunca se comparten ni se versionan.

## Alternativas consideradas

| Alternativa | Evaluacion para este alcance |
|---|---|
| WireGuard directo con wg e ip | Elegida en el checkpoint: pares preparados, endpoints alcanzables y ciclo de vida explicito |
| wg-quick con perfiles arbitrarios | Se evita aceptar hooks o comandos de shell en perfiles privilegiados |
| Tailscale con coordinacion alojada | No se elige para el alcance aprobado; introduciria otra infraestructura que evaluar |
| Cliente Tailscale con Headscale propio | No se elige: operacion y disponibilidad de un coordinador adicional fuera del alcance de dos pares preparados |

## Decision

### Preparacion previa, separada de join

Cada equipo genera su propia clave localmente con las herramientas de WireGuard.
La privada permanece en ese equipo, en un directorio root:root 0700 y archivo
0600, fuera del repositorio. Solo se intercambian clave publica, direccion del
par y endpoint, confirmando su origen con la otra persona.

Un perfil local administrado por root declara la clave propia, clave publica del
par, direcciones IPv4 del tunel, IP numerica del endpoint y puerto. Se proponen
`/etc/nimbo-net/perfil.json` y un archivo de clave protegido. No admite hooks ni
comandos, ni enlaces simbolicos o escritura por usuarios ajenos. Antes de usarlo
se validan formato, permisos, rutas y conflictos. La preparacion no levanta la
interfaz ni abre el puerto. Las pruebas generan sus propias claves efimeras.

### Activacion y limpieza

- `sudo nimbo-net join`: usa un perfil previamente preparado, sin argumentos
  obligatorios. Comprueba la red fisica disponible mediante el contrato de
  `nimbo-red`; si falta, indica `sudo nimbo-red on` y falla sin activar la VPN.
  No invoca DHCP ni levanta interfaces fisicas por su cuenta.
- Se confirma **wg-nimbo** como nombre de interfaz. Coincide con
  `INTERFAZ_NIMBO_NET` y `AssertPathExists=!/sys/class/net/wg-nimbo` de Emmanuel,
  ya presentes en main 8d01002. Una interfaz ajena con ese nombre es un conflicto,
  no un recurso que se pueda borrar o adoptar silenciosamente.
- Se configura con wg e ip mediante listas de argumentos, sin shell. Tunel
  dividido: direcciones/rutas de los pares, sin ruta por defecto, cambios de DNS,
  forwarding ni NAT. IPv4 es el alcance inicial; no se desactiva IPv6 del sistema.
- Join solo informa conexion tras handshake y trafico de prueba al par con espera
  acotada. Dos equipos que ejecutan join uno despues del otro deben disponer de
  una ventana de espera documentada; interfaz creada no significa conectado.
- `nimbo-net status` permite consultar estado sin revelar secretos.
  `sudo nimbo-net leave` retira solo interfaz, rutas y estado creados por nimbo-net.
  No ejecuta `nimbo-red off` ni elimina recursos de otros modulos.
- Fallos y timeout requieren limpiar los recursos propios. Repeticiones de join
  o leave no deben duplicar recursos. Se serializan operaciones del modulo.
- No se instala servicio de arranque ni se activa keepalive persistente por defecto.
  Tras reinicio, el tunel esta inactivo; las identidades locales pueden persistir.

### Exclusion mutua con Tor y reglas de red

Join se niega antes de modificar red si existe la tabla `inet nimbo_tor` o si
`nimbo-modo-tor.service` esta activo o en transicion de arranque/parada. Si no se
puede determinar el estado, falla con diagnostico; no interpreta un error de
consulta como prueba de que Tor esta apagado.

En sentido inverso, nimbo-tor on ya comprueba la existencia de wg-nimbo y la
unidad systemd incorpora la misma barrera. nimbo-net no modifica esos archivos.
La prueba incluye ambos ordenes y activaciones concurrentes: las comprobaciones
por si solas no acreditan exclusion atomica. Si se observa una carrera, se acuerda
con Emmanuel un mecanismo compartido antes de declarar aceptacion; cualquier
cambio a su modulo o a la integracion se revisa con sus responsables.

Si hacen falta reglas nftables, se limitan a una tabla propia `inet nimbo_net`;
la limpieza elimina solo esa tabla. **Nunca flush ruleset**, ni borrar o modificar
`nimbo_tor`. No se intenta habilitar la VPN mediante excepciones a la politica Tor.
No se agrega una tabla sin una necesidad concreta y su prueba.

### Compatibilidad con hardening

Se mantiene **rp_filter=1**: no se cambian sysctl automaticamente. Con el tunel
arriba se registran los valores efectivos de all, default, interfaz fisica y
wg-nimbo, las rutas y el resultado bidireccional. Se aplica el hardening vigente
`99-zz-nimbo-hardening.conf`. Si hay un fallo atribuible al filtrado inverso,
se entrega evidencia y se solicita un checkpoint para valorar 2. No se declara
compatibilidad medida hasta ejecutar esa prueba. Tunel completo fuera de v1.

## Verificacion y criterios de aceptacion

| Prueba | Pasa si |
|---|---|
| Tests del modulo, rojo antes de implementar | CLI y validacion rechazan perfiles invalidos, permisos debiles, conflictos, errores de sistema y timeout sin secretos ni residuos |
| Bookworm anclado | Tests con ci/test-modulo-en-bookworm.sh, dependencias APT acordadas; agregar un job requiere checkpoint |
| Dos VMs/equipos, claves generadas localmente y perfiles preparados | Un join por equipo, handshake y trafico bidireccional verificables con rp_filter=1 |
| Captura fisica y captura del tunel | Transporte WireGuard entre endpoints; marcador de prueba visible solo en el tunel, no en claro en la fisica |
| Tor primero y VPN primero | El segundo modo se niega sin borrar recursos del primero; probar tambien activacion concurrente |
| Antes de join y tras reiniciar | Sin wg-nimbo, socket VPN, servicio ni actividad automatica; hermetismo global 0 sospechosos / 0 listeners |
| Leave y fallos | Sin recursos VPN propios; red fisica y recursos ajenos conservados; rutas por defecto y DNS sin cambios atribuibles a nimbo-net |
| Silencio global tras usar red | Se mide despues de nimbo-red off; leave no apaga la red fisica |

Se registran comandos, codigos de salida y evidencia sin credenciales. Tests con
un ejecutor simulado no sustituyen dos VMs, handshake ni captura real. La
integracion en la ISO exige checkpoint y MATCH x2; QEMU y hardware se coordinan
con Juan Jose. No hay pruebas de VPN ejecutadas al redactar este ADR.

## Consecuencias

Se obtiene una red cifrada entre pares preparados, sin coordinador ni actividad
VPN al arrancar. Se paga la preparacion de perfiles y el requisito de endpoints
alcanzables. No hay descubrimiento automatico, relay, CGNAT garantizado, Wi-Fi,
tunel completo ni ejecucion simultanea con Tor en v1. No cifra automaticamente
la navegacion ni comparte archivos por si solo.

## Fecha

2026-11-11
