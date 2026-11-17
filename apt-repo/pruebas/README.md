# Reproducción del laboratorio APT

Usar una VM Bookworm desechable, no la ISO nimbo ni un equipo de trabajo.
El laboratorio instala herramientas de build y los cinco módulos, y apaga la VM.
No genera ni configura la clave real de release.

1. Descargar la imagen oficial debian-12-genericcloud-amd64.qcow2 y su SHA512SUMS
   desde https://cloud.debian.org/images/cloud/bookworm/latest/. Registrar URL,
   hash y tamaño. El ensayo compara el hash de la imagen con ese archivo
   obtenido por HTTPS; no lo presenta como una verificación OpenPGP del origen.
2. Crear un overlay nuevo de 24 GiB; QEMU/TCG, q35, 4096 MiB y 2 vCPU.
   Primera serie a un log, segunda serie a otro fichero para el resultado.
3. Preparar una copia de apt-repo/ y release/ que corresponda al código probado,
   y source.bundle con refs/remotes/origin/main. El bundle contiene solo el
   historial público necesario. La VM obtiene esos archivos mediante un servidor
   HTTP del host limitado a loopback, accesible como 10.0.2.2 desde SLIRP.
4. NoCloud recibe meta-data con instance-id nuevo y user-data que descarga esas
   fuentes a /media/nimbo, crea /run/nimbo-apt-lab-autorizado y ejecuta vm-lab.sh.
   No hay usuarios con contraseña ni claves de acceso configuradas.
5. Usar SMBIOS ds=nocloud-net con la URL local de la semilla. El ensayo inicial
   mediante CD no activó los scripts; se corrigió la detección a NoCloud por HTTP.
6. vm-lab.sh registra el estado inicial sin módulos nimbo. Instala Docker/aptly/GPG
   en la VM de prueba, corre los tests, construye dos veces desde el mismo commit
   mediante el contenedor anclado y compara BUILD.json.
7. publicar.sh/aptrepo preparan el sitio; firmar-efimero.py crea una identidad de
   prueba exclusivamente dentro de la VM y firma reutilizando release/.
   cliente-vm.py verifica, descarga e instala con APT real las versiones exactas.
   Las dependencias Debian vienen de sus fuentes Debian, no del repositorio nimbo.
8. La prueba negativa de identidad usa una lista APT vacía y solo la fuente
   de prueba: no se da por válido el fallback a índices de una ejecución anterior.
9. Al terminar se exportan únicamente evidencia/, builds públicos y sitio público
   por ttyS1, entre NIMBO_APT_EVIDENCIA_BEGIN/END, como tar gzip en base64.
   Normalizar CRLF antes de decodificar. No se exporta el directorio de claves.
   Los discos y el log completo de arranque quedan fuera del repositorio.

La VM demuestra instalación del candidato con firma efímera y las pruebas
negativas. La firma real, el despliegue Pages y la aceptación del tag v1.0.0
son pasos posteriores con aprobación de Juan José. Los hash de las fuentes
de instrumentación usadas se deben conservar junto a los resultados.

Para aceptar v1.0.0, ejecutar dentro de la VM Bookworm limpia también
`python3 -m unittest discover -s apt-repo/tests -p test_apt_transport.py -v`:
APT real debe rechazar InRelease alterado, paquete alterado y clave incorrecta.
Es un requisito adicional a instalar las versiones exactas desde Pages;
registrar ambas evidencias y el commit del tag final.
