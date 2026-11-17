# Checkpoint de apt-repo.yml para Juan José

Preparado después de los scripts, tests y evidencia en VM del 16-nov.
Checkpoint aprobado y #91 mergeado. El candidato fue firmado y publicado
con aprobación de Juan José en el run 43952639106. No es el corte final v1.0.0.

## Entrada y jobs

- PR: solo tests en el contenedor Bookworm anclado, sin secretos.
- workflow_dispatch desde main: modo candidato-main o v1.0.0; publicar=false por
  defecto. El candidato toma github.sha, no una rama móvil durante el build.
  El final exige el tag v1.0.0, su commit exacto y que pertenezca a main.
- preparar: dos contenedores independientes construyen los cinco módulos con
  la receta de la ISO. BUILD.json debe coincidir. aptly genera el sitio sin
  firma; el verificador valida paquetes y metadatos antes de subirlo.
- firmar: solo con publicar=true y environment release aprobado. Descarga el
  artifact por ID, comprueba el digest ZIP de upload-artifact, el SHA-256 del
  TAR y el digest del árbol fijados por preparar. Revalida. No hay apt-get,
  aptly, Docker ni reconstrucción en este job. Los secretos solo aparecen en
  el paso que reutiliza firmar.py; firma InRelease y Release.gpg.
- preparar-pages: recibe el artifact público firmado, vuelve a comprobar los
  tres digests y verifica con el certificado independiente versionado.
  Crea el artifact especial de Pages.
- desplegar: solo pages:write e id-token:write, environment github-pages.
  Sin secretos de firma ni contenido construido en ese job.

Permisos por defecto contents:read. actions:read solo donde se descarga vía API.
Todas las acciones están fijadas a SHA completo de versiones oficiales.
Concurrency de despliegue única, sin cancel-in-progress. El workflow no cambia
permisos/configuración de environments ni usa una clave privada fuera de release.

## Políticas externas necesarias

Juan José ya configuró release con required reviewer Duque-Londono y rama main.
La política de ramas protege los secretos incluso si otro YAML omitiera el if.
Pages está activado con origen Actions; github-pages solo admite main.

Pages sustituye el SITIO ENTERO en cada despliegue. El artifact contiene
index.html, .nojekyll y apt/. Hoy está vacío; si aparece otro contenido antes
del merge, hay que integrarlo en el artifact antes de publicar.

## Caducidad y estado de entrega

Valid-Until = Date + 30 días, comprobado antes y después de firmar.
Esperar aprobación no renueva la fecha. Un artifact caducado se rechaza.
La renovación la aprueba Juan José y empieza con nuevos metadatos verificados,
sin alterar la procedencia de los paquetes si sus bytes se conservan.

La evidencia actual acredita candidato de main con firma efímera. No equivale
a un repositorio publicado con la clave real ni a RF-DIST-01 final. Para nuevas
publicaciones: ejecutar primero publicar=false; revisar artifact. Para desplegar,
nuevo dispatch publicar=true y aprobación de Juan José. La aceptación final
requiere el modo v1.0.0, publicación y prueba contra las URL reales.

Plan B aprobado: si el workflow no llega al 23-nov, Juan José firma manualmente
una vez el artifact verificado con estas herramientas. No se relaja la política
de firma, de procedencia ni de caducidad.

## Validación previa

- Local: 48 tests de release y 28 de APT; sin claves reales.
- VM Bookworm: 48 tests de release y 24 de APT de la instrumentación inicial;
  doble compilación idéntica e instalación real de los cinco módulos.
- Los cuatro tests APT añadidos después comprueban update/download válido y
  rechazo real de metadatos, deb o identidad alterados con estado temporal.
- Pipeline local con el sitio real de la VM: ZIP/TAR/árbol coinciden y verificación
  completa correcta. actionlint 1.7.12 acepta el YAML; shellcheck no ejecutado.
- Primera ejecución real y despliegue candidato completados: run 43952639106.
  Juan José verificó desde Bookworm limpio huella, update e instalación exacta;
  otra clave fue rechazada. Queda repetir con v1.0.0, incluyendo dentro de la
  VM las pruebas negativas de InRelease, deb y clave alterados.

## Notas del checkpoint #91

La función de firma compartida usa --digest-algo SHA256 fijo, también para
el release ISO. aptly en el runner se obtiene del APT de Ubuntu sin versión
fijada: los deb son reproducibles; los metadatos se verifican y firman.
El detalle y la batería negativa obligatoria en VM para v1.0.0 están en README.md.
