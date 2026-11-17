# Repositorio APT nimbo — RF-DIST-01

Dueño: Alejandro, con revisión de Juan José. Este directorio implementa el
candidato; **no acredita todavía la publicación del tag final v1.0.0**.

Distribución: bookworm/main, amd64 y paquetes all. Incluye los cinco módulos de
la lista única de la ISO. No añade una fuente APT a la ISO: conectarse y añadir
la fuente son acciones expresas de quien administra el cliente.

## Construcción y repositorio local

build-packages.sh recibe una salida nueva y un commit. Exporta solo los archivos
versionados de ese commit y usa la imagen y snapshot de su receta de ISO.
SOURCE_DATE_EPOCH es la fecha del commit. Construye los cinco módulos mediante
apt-get build-dep y dpkg-buildpackage, sin construir una ISO. BUILD.json registra
commit, epoch, snapshot, imagen y SHA-256 de cada deb.

Ejecutar dos builds y comparar BUILD.json y los cinco hashes antes de promover.
No reutilizar salidas existentes. El modo --final de preparar exige que el tag
local v1.0.0 apunte al commit indicado; el modo por defecto siempre es candidato. Las excepciones de caducidad de los archivos
históricos Debian quedan limitadas a los contenedores de construcción; no se
aplican a la fuente APT nimbo.

publicar.sh genera **solo un sitio local sin firma**, mediante repositorio y
snapshot de aptly. Recibe --debs, --salida, --commit, --epoch, --snapshot e
--image (digest sha256 completo de la imagen, sin nombre). Verifica BUILD.json.
No despliega. aptly publica los índices; antes de firmar se añaden Date,
Valid-Until y PROCEDENCIA.json cubierto por SHA256 de Release.

## Firma y verificación

La clave pública versionada es ../release/nimbo-release-publica.asc.
Huella primaria autorizada:

**0C50 B739 1A9B 8CFF 8A36 A627 D3B9 111F EC57 48C6**

Contrastar también README raíz y docs/sustentacion/README.md. El certificado del
propio repositorio no sustituye un canal independiente: puede omitir una revocación.
verificar.sh permite --clave con un certificado actualizado de esa misma identidad;
se importan ambos conservando revocaciones conocidas.

Se reutilizan signing_key, select_subkey y sign_document de release/firmar.py.
Solo se admite una subclave de firma vigente con caducidad y una primaria secreta
no disponible. El llavero es temporal y no hereda confianza ni recupera claves.
Los secretos se leen del environment y se retiran antes de crear subprocesos.
La firma toma un sitio cuyo digest coincide con el fijado al verificarlo; no
ejecuta builds ni cambia índices. Produce InRelease y Release.gpg.

verificar.sh exige una GOODSIG y una VALIDSIG de la primaria autorizada.
Rechaza REVKEYSIG, EXPKEYSIG, EXPSIG, BADSIG, ERRSIG, NO_PUBKEY y los estados
de caducidad/revocación adicionales que rechaza release.py. Comprueba ambas
firmas, igualdad InRelease/Release, fecha, hashes de índices y debs, cabeceras,
los cinco módulos y procedencia; rechaza enlaces y contenido extra.

## Caducidad

Release caduca exactamente 30 días después de Date. Limita la aceptación de
metadatos antiguos, pero exige un reloj correcto y renovación operativa.
Juan José aprueba la renovación: se vuelve a preparar Date/Valid-Until, verificar
y firmar con la misma procedencia y paquetes cuando no cambian sus bytes.
No se renueva al firmar un artifact existente, ni se falsea SOURCE_DATE_EPOCH.
El repositorio vencido se rechaza; la guía no ofrece un bypass.

## Cliente, después de la publicación aprobada

URL prevista: https://teamlocknet.github.io/nimbo/apt/. No usar hasta el
despliegue aprobado. Obtener el certificado por el canal independiente,
comprobar su huella y copiarlo como /usr/share/keyrings/nimbo-release.asc
(archivo público, modo 0644). La fuente es:

    deb [arch=amd64 signed-by=/usr/share/keyrings/nimbo-release.asc] https://teamlocknet.github.io/nimbo/apt/ bookworm main

Después, apt-get update, apt-cache policy y apt-get download/apt-get install
con nombre=versión para cada módulo de PROCEDENCIA.json. APT verifica InRelease
y la cadena de hashes; las dependencias Debian proceden de las fuentes Debian
del cliente. No usar apt-key ni trusted=yes. El cliente no habilita servicios
de VPN/Tor automáticamente: conserva el comportamiento de los paquetes.

## Pages y entrega

GitHub Pages desde Actions reemplaza TODO el sitio en cada despliegue, no
solo /apt. El artifact incluirá raíz index.html, .nojekyll y apt/. Si se añade
documentación u otro contenido al sitio, se debe incluir aquí antes de desplegar:
no se preserva automáticamente el despliegue anterior.

Environment release: aprobación de Juan José y solo main.
Environment github-pages: solo main. El workflow se presenta después de la
evidencia en VM para su checkpoint; no se despliega desde una rama de PR.
Si no llega a tiempo, Juan José puede firmar manualmente una vez el artifact
ya verificado, usando las mismas herramientas y su propia custodia.

## Pruebas

test-local.sh ejecuta la batería de release y apt-repo con claves efímeras.
Requiere python3, gnupg, aptly, dpkg-deb y bzip2. Incluye firmas reales de una
subclave revocada y otra caducada después de firmar. Una mutación que elimina
el criterio de estados hace fallar ambas pruebas.

pruebas/vm-lab.sh solo corre en una VM Bookworm desechable preparada para ello.
Comprueba que los cinco módulos no estén instalados, ejecuta tests, compila
dos veces mediante el contenedor anclado, firma con una clave efímera y usa
APT real para descargar/instalar versiones exactas y rechazar otra identidad.
Su firma es solo de laboratorio: no sustituye la aprobación/firma real de Juan José.

Referencias de formato: [aptly publish snapshot](https://www.aptly.info/doc/aptly/publish/snapshot/)
y [manual de aptly en Bookworm](https://manpages.debian.org/bookworm/aptly/aptly.1.en.html).
