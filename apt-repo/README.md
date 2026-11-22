# Repositorio APT nimbo — RF-DIST-01

Dueño: Alejandro, con revisión de Juan José. Este directorio implementa el
repositorio APT firmado. El corte final **v1.0.0** está publicado y su validación
en VM Bookworm limpia consta en [la evidencia del 22-nov](evidencia/2026-11-22-v1.0.0/RESULTADOS.md).
Juan José aceptó RF-DIST-01 al revisarla y mergear #119.

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
No despliega. En el runner ubuntu-24.04, aptly se instala desde el repositorio
APT de Ubuntu **sin fijar su versión**. La reproducibilidad comprobada corresponde
a los paquetes .deb construidos con imagen, snapshot y epoch anclados. No se
promete igualdad byte a byte de los metadatos generados por distintas versiones
de aptly: esos metadatos se verifican y se firman.

aptly publica los índices; antes de firmar se añaden Date,
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
La función compartida fija --digest-algo SHA256; se aplica tanto a InRelease y
Release.gpg como a la firma SHA256SUMS del release de la ISO.
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

Final v1.0.0 publicado: https://teamlocknet.github.io/nimbo/apt/.
[Run aprobado 44824465730](https://github.com/teamlocknet/nimbo/actions/runs/44824465730),
paquetes de 94f9b8fec60938baccae984f891cc3ac6960e109. La procedencia declara
candidate=false y release_tag=v1.0.0. Valid-Until: **20-dic-2026, 21:57:48 UTC**.
El candidato anterior se publicó en el run 43952639106; esta validación lo sustituye
como evidencia del corte final.
Obtener el certificado por el canal independiente,
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

## Validación obligatoria del corte v1.0.0

**Completada el 22-nov-2026:** descarga desde Pages, huella y ambas firmas
correctas, procedencia del tag y cinco versiones exactas instaladas en una VM
Bookworm limpia. [Resultados, hashes y códigos de salida](evidencia/2026-11-22-v1.0.0/RESULTADOS.md):
37/37 comprobaciones y los cuatro tests APT correctos. InRelease alterado, deb
alterado y clave incorrecta rechazados con código 100. Revisado y aceptado por
Juan José (#119).

Para repetir en otro corte, comprobar descarga desde Pages, huella/firma,
procedencia del tag e instalación de las cinco versiones exactas.
En ESA VM ejecutar también las pruebas negativas con APT real, desde el checkout
del código de pruebas del corte:

```sh
python3 -m unittest discover -s apt-repo/tests -p test_apt_transport.py -v
```

Estas pruebas usan un repositorio local efímero y estado temporal de APT;
no alteran el repositorio publicado. Exigen rechazo de InRelease alterado,
paquete alterado y clave incorrecta, además del control positivo de descarga.
Conservar la salida y códigos de salida junto a la evidencia positiva de Pages,
commit del tag, versiones y hashes. La evidencia local/CI del candidato no
sustituye estas pruebas en VM para aceptar RF-DIST-01 final.
