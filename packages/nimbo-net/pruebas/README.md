# Evidencia para dos VMs

Usar VMs desechables del laboratorio coordinado con Juan Jose. No ejecutar join,
leave, DHCP o cambios de firewall en el anfitrion para esta validacion.
Cada VM genera su clave local y recibe solo datos publicos del otro par; seguir
la preparacion de ../README.md. Perfil y claves no se versionan ni se envian.

recoger-evidencia.py es una consulta pasiva (sin ping ni cambios de configuracion):

```bash
sudo python3 recoger-evidencia.py reposo
# Despues de nimbo-red on y un nimbo-net join por equipo:
sudo python3 recoger-evidencia.py tunel
# Despues de nimbo-net leave y nimbo-red off:
sudo python3 recoger-evidencia.py limpio
```

Guardar las salidas fuera del repo y revisarlas antes de publicar evidencia.
Registra version, rutas, hash de resolv.conf, handshake/counters, rp_filter y
listeners. No imprime claves ni salidas wg dump/showconf/private-key.
No genera ni solicita credenciales. Los contadores de trafico son historicos:
no sustituyen una prueba bidireccional actual ni una captura de la NIC y tunel.

Preparar dos instancias con IP fisica alcanzable, perfiles cruzados y Tor apagado.
Registrar rutas y DNS antes/despues; probar ping en ambas direcciones tras join.
Medir rp_filter=1 con hardening aplicado y tunel activo. Verificar por separado
Tor primero, VPN primero e intentos concurrentes con Emmanuel. Si hay carrera,
resolverla con checkpoint antes de cerrar RF-RED-01.

Una instantanea de ss no demuestra 0 conexiones salientes. La captura real y el
hermetismo global corresponden al procedimiento de ISO/QEMU del equipo revisor.
Herramienta nueva: solo sintaxis y --help comprobados; no ejecutada en VMs reales.
