# RF-DIST-01: resultado del corte v1.0.0

**Resultado:** instalación desde el APT final en VM Bookworm limpia y pruebas
negativas correctas, el 22-nov-2026. 37/37 comprobaciones en COMPROBACIONES.json.
La aceptación del requisito corresponde a Juan José al revisar esta evidencia.

## Procedencia y entorno

- URL real, sin autenticar: https://teamlocknet.github.io/nimbo/apt/.
- [Workflow 44824465730](https://github.com/teamlocknet/nimbo/actions/runs/44824465730),
  intento 1, workflow_dispatch desde main 23cd07974fad0037904ab71cdb75323a79957559.
  Los cinco jobs terminaron en success, incluida la firma aprobada por Juan José
  y el despliegue. workflow-publicacion-final.json y workflow-jobs-final.json.
- Tag y checkout de pruebas: **94f9b8fec60938baccae984f891cc3ac6960e109**.
  Se clonó v1.0.0 directamente desde el GitHub público; HEAD y el tag coinciden.
  git-head.*, git-tag.* y git-status.* conservan las consultas.
- Dos builds independientes del contenedor anclado produjeron los mismos hashes
  de los cinco deb. BUILD-REPRODUCIBILIDAD.json conserva el extracto de ambas
  salidas y la identificación del job; también nimbo-nav coincidió. Los hashes
  publicados y los descargados por APT coinciden con esos builds.
- VM cliente Debian 12 Bookworm sobre la imagen cloud oficial identificada por
  URL, tamaño y SHA-512 en PREPARACION-IMAGEN-BASE.json. Overlay nuevo preparado
  el 18-nov; QEMU TCG, 3 GiB, 2 vCPU. Kernel medido:
  6.1.0-56-cloud-amd64. No es una prueba de la ISO nimbo.
- Antes de añadir la fuente se repitió el control: los cinco módulos ausentes,
  ninguna fuente nimbo y ninguna huella nimbo en /etc/apt/trusted.gpg,
  /etc/apt/trusted.gpg.d/ y /usr/share/keyrings/. BASELINE.json y uname.*.
  apt, gnupg, python3, aptly, git y qemu-guest-agent están identificados en version-*.
  El agente QEMU solo es instrumentación de esta VM de laboratorio.

## Firma, metadatos y hashes

Huella primaria autorizada: **0C50B7391A9B8CFF8A36A627D3B9111FEC5748C6**.
Se obtuvo el certificado por el canal independiente del repositorio, fijado al
commit del workflow, además del certificado servido por Pages. Coincide también
con el certificado de main consultado al validar. Ambos son solo públicos.
DESCARGAS.json registra URL, fecha, bytes y SHA-256 de cada descarga HTTP.

Se importaron ambos certificados en un llavero temporal aislado. InRelease y
Release.gpg devolvieron 0, una GOODSIG y una VALIDSIG de la primaria autorizada,
sin estados de revocación, caducidad ni error, conforme a release.py. Se comprobó
la igualdad del texto de InRelease con Release. Salidas: firma-inrelease.*,
firma-separada.* y huella.*. No se hereda confianza ni se recuperan claves.

El verificador aptrepo.verify_tree del tag comprobó todos los índices, paquetes,
cabeceras y procedencia sobre la copia completa descargada en la VM. Los hashes
se verificaron antes de interpretar PROCEDENCIA.json. La procedencia declara:

- candidate: false; release_tag: v1.0.0.
- commit: 94f9b8fec60938baccae984f891cc3ac6960e109.
- suite/componente: bookworm/main.
- Imagen: debian@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171.
- Snapshot: 20260901T000000Z; SOURCE_DATE_EPOCH: 1795138255.
- Date: **20-nov-2026 21:57:48 UTC**; Valid-Until:
  **20-dic-2026 21:57:48 UTC**, 30 días exactos. Date corresponde a la preparación
  de metadatos; la aprobación y publicación terminaron el 21-nov.

## Instalación contra Pages

Se añadió exclusivamente en la VM la fuente con signed-by y el certificado
independiente comprobado, modo 0644. nimbo-final-validacion.list conserva la
fuente. APT mantiene sus verificaciones habituales de autenticidad y caducidad.
Las dependencias proceden de las fuentes Debian de la VM.

apt-get update con APT::Update::Error-Mode=any, apt-get download e install con
nombre=versión devolvieron 0. apt-policy.* identifica Pages como origen; las
cinco descargas coinciden con los hashes firmados y dpkg-query confirma ii:

| Paquete | Versión instalada | SHA-256 del deb descargado por APT |
|---|---|---|
| nimbo-audit | 0.1.0-1 | `a54cea66c33eaec8df82a5bddc26c403ae4cf3fbfa1dc0378e0f1429834cf131` |
| nimbo-nav | 0.1.5-1 | `ec8e56b9f7d2cad1563ac9833c42e329c386bdcb94fa323bccaf839040132873` |
| nimbo-net | 0.1.0-1 | `bdf09ed9439565cf3366652f6fbe2385fe2dc64fd29dc2965d5ec1cf3f764ffd` |
| nimbo-red | 0.1.1-1 | `b9caa6a91fa3e3ba889c2d7ffdd1e499077857716e8919ca5fa84a7d46f359c0` |
| nimbo-update-offline | 0.1.2-1 | `6a0b36244bb647a1351c2f8dbe050cc4104d6ba7094a2926c56d214517eaf520` |

Salidas completas y códigos: apt-update.*, apt-policy.*, apt-download.*,
apt-install.* y dpkg-instalados.*. HASHES-descargas-apt.json conserva las sumas.
APT emitió en download un aviso de descarga como root al no poder acceder _apt
al destino; se conserva en apt-download.stderr.log. La descarga tuvo código 0
con autenticación y hashes comprobados. apt-install.stderr.log está vacío.

## Pruebas negativas en la misma VM

Desde el checkout del tag, sin modificar sus pruebas:

```sh
python3 -m unittest discover -s apt-repo/tests -p test_apt_transport.py -v
```

**4 tests OK; código global 0.** test-apt-transport.* conserva comando y salida.
Los tests usan repositorios locales con claves efímeras y estado APT temporal;
las instalaciones positivas anteriores sí usan Pages y la clave real pública.
No se alteró la publicación para ensayar los ataques.

| Caso | Operación APT | Código real | Resultado esperado |
|---|---|---|---|
| Deb alterado | update, download | 0, 100 | Hash/tamaño no válido: rechazado |
| InRelease alterado | update | 100 | Firma no válida: rechazado |
| Clave incorrecta | update | 100 | Identidad no disponible: rechazado |
| Control válido | update, download | 0, 0 | Descarga aceptada |

apt-negativas-subprocesos.jsonl conserva argv, stdout, stderr y exit_code de las
seis llamadas APT, etiquetadas por test. Un observador externo en
instrumentacion/sitecustomize.py recoge los valores reales de subprocess.run,
sin cambiar argumentos ni resultados. PYTHONPATH solo añade ese observador;
el código de los tests del tag queda intacto, comprobado al terminar.

## Repetición y archivos publicados

validar-final-vm.py es la instrumentación utilizada, externa al checkout. En una
VM limpia con las herramientas de la preparación del 18-nov, clonar el tag
v1.0.0 en /var/tmp/nimbo-v1.0.0 y ejecutar como root en la VM, en este orden:

```sh
python3 validar-final-vm.py verificar
python3 validar-final-vm.py instalar
python3 validar-final-vm.py negativas
```

La salida por defecto es /var/tmp/nimbo-apt-final-evidencia. Las fases se niegan
a repetir una fase ya completada. La instrumentación requiere el tag y las
versiones de este corte; verifica antes de instalar. No firma material real.

En Git se conservan metadatos públicos, certificado, salidas, códigos y hashes.
Los deb se verificaron en la VM y se omiten de esta carpeta para no duplicar
binarios. Por ello pages/ es una copia documental de los metadatos, no un espejo
instalable completo. .nojekyll es un marcador vacío creado localmente para el
verificador del árbol; no se descargó de Pages. Esto consta en verificar-OK.json.

SHA256SUMS-VM se generó dentro de la VM y se comprobó tras transferir los archivos.
SHA256SUMS cubre además los resultados y la trazabilidad añadida en el host.
No se incluyen discos, llaveros privados ni claves privadas de prueba o release.

Si la sustentación cae después de Valid-Until, corresponde renovar con aprobación
de Juan José. Esta evidencia no modifica la ISO, CI ni el despliegue publicado.
