# RF-DIST-01: candidato probado en Bookworm

**Resultado del ensayo: OK**, 16-nov-2026. No es la publicación final v1.0.0.

Fuente de los cinco paquetes: main
eb3bc36c5769654adbd280b49a2d5f90b2155299. El commit, epoch, snapshot,
digest de imagen y hashes están en build-A.json y build-B.json.
Los dos archivos coinciden byte a byte; los cinco deb de dos contenedores
independientes también coinciden. Se usó la secuencia apt-get build-dep +
dpkg-buildpackage de la receta de ISO, sin construir ni modificar una ISO.

| Módulo | Versión candidata instalada |
|---|---|
| nimbo-audit | 0.1.0-1 |
| nimbo-red | 0.1.1-1 |
| nimbo-update-offline | 0.1.1-1 |
| nimbo-nav | 0.1.0-1 |
| nimbo-net | 0.1.0-1 |

## Entorno y comprobaciones

VM nueva desde imagen oficial Debian 12 genericcloud, con overlay de 24 GiB,
QEMU/TCG, q35, 4096 MiB y dos vCPU. imagen-bookworm.json registra URL, tamaño
y SHA512 cotejado con SHA512SUMS obtenido por HTTPS. No se afirma verificación
OpenPGP de esa imagen. No se usó la ISO nimbo.

El estado inicial no tenía ninguno de los cinco módulos. Se instalaron
herramientas de laboratorio (Docker, aptly 1.5.0, GnuPG 2.2.40, Git, pytest);
los builds de producto se hicieron dentro de la imagen anclada por digest.
No se afirma que las herramientas instaladas en la VM sean la toolchain
del build: la toolchain anclada está dentro de cada contenedor.

- 48 tests de release y 24 de APT pasan en Python 3.11 de Bookworm.
- aptly genera bookworm/main, con índices amd64/all.
- Release tiene Valid-Until exactamente 30 días después de Date.
- Firma efímera de laboratorio: InRelease y Release.gpg, con las funciones
  compartidas de release/. Certificado y huellas públicas adjuntos.
- APT real actualiza índices, descarga las cinco versiones exactas, comprueba
  hashes e instala. cliente.json conserva comandos, salidas y códigos.
- La prueba negativa de identidad usa listas vacías y solo la fuente de prueba;
  APT devuelve error al verificar con otra clave. No se acepta fallback.
- Todas las ayudas ejecutan correctamente. instalados.txt registra las versiones.
- Limpieza de la fuente temporal y apagado de la VM. exit-code = 0.

La clave efímera tiene caducidad corta y su parte privada se descartó. Este
certificado no se debe instalar ni publicar como clave oficial. Tras caducar,
la política estricta rechazará su firma; el registro conserva la observación
realizada el 16-nov y los hashes de evidencia. La clave oficial no se utilizó.

## Rojo y verde de la política GPG

Las pruebas generan firmas reales con subclave revocada y con subclave caducada
después de firmar. Rechazo correcto. La mutación que omite signature_status
hace fallar ambos tests: mutacion-estados.txt. Esto demuestra que un VALIDSIG
y código 0 de gpgv no bastan.

Después del ensayo se añadieron cuatro pruebas con APT real y estado temporal:
update/download válidos; rechazo de InRelease alterado, paquete alterado y
clave incorrecta. Local: 48 + 28 pruebas correctas, tests-locales.txt.

El verificador actual vuelve a aceptar el sitio firmado del ensayo. Se probaron
también empaquetado TAR y recepción ZIP con el sitio real: pipeline-local.json.
No se reconstruyen ni cambian los paquetes al recibir o firmar un artifact.

## Procedencia y límites

instrumentacion-sha256.json identifica los archivos copiados a la VM.
El primer arranque no detectó la semilla de CD; se pasó a NoCloud por HTTP
local. Un primer ensayo detectó que faltaba exportar NIMBO_SNAPSHOT al
contenedor; se corrigió y se repitió desde un disco limpio. El ensayo exitoso
es v3; los intentos fallidos permanecen en la caché privada, no se presentan
como evidencia de instalación correcta.

Las mejoras posteriores de límites de índices y pruebas de transporte están
cubiertas por los tests locales; no se atribuyen retrospectivamente al código
ejecutado dentro de la VM. No se exportan discos, claves privadas ni credenciales.
Los paquetes y el sitio completo se conservan fuera del repo; aquí se guardan
metadatos, resultados y hashes. SHA256SUMS cubre los archivos de esta evidencia.

Pendiente: checkpoint y ejecución real de apt-repo.yml, firma oficial y primer
despliegue. RF-DIST-01 se cerrará al publicar los paquetes del tag v1.0.0 y
repetir descarga, verificación e instalación desde la URL pública.

El log de ejecución publicado normaliza CR/LF y espacios finales para su lectura.
Su hash original está registrado en ejecucion-original-sha256.txt. Los metadatos
firmados no se transforman; .gitattributes conserva exactamente sus bytes.
