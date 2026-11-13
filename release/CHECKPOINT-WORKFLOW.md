# Workflow del release firmado: implementacion para revision

Este documento concreta el diseño y las condiciones aprobadas por Juan José.
.github/workflows/release.yml está implementado en una rama para su revisión;
no se ha ejecutado, mergeado ni publicado ningún release.

## Entrada y compuertas

workflow_dispatch desde refs/heads/main, con tag, SHA completo, build_run y
repro_run explícitos. Primer candidato aprobado: v1.0.0-rc1,
03ff84cd1804908cbd1fd7cdb90c0e8c1734a5fa, build 42850483095,
repro 42850482997. La consulta del 11-nov confirma main/push/success y las
rutas build-iso.yml y repro-verify.yml para ese SHA.

Límite real del conjunto: **17-nov-2026 a las 16:11:04 UTC**, cuando caduca
iso-sha-B, antes que la ISO. Fechas observadas en la revisión de Juan José:

| Artifact | Run | Caducidad UTC (17-nov-2026) |
|---|---|---|
| iso-sha-B | 42850482997 | 16:11:04 |
| nimbo-iso-03ff84c (13781341509) | 42850483095 | 16:11:17 |
| iso-sha-A | 42850482997 | 16:12:03 |

Antes de firmar, consultar la API del repositorio fijo teamlocknet/nimbo:

1. Ambos runs finalizados con success, SHA exacto, main y origen permitido;
   comprobar ruta/identidad del workflow. No aceptar PRs ni repos externos.
2. Artifact exacto del run, no caducado; descargar y cotejar su digest de archivo
   con la API antes de extraer. Rechazar rutas externas, enlaces y archivos extra.
3. SHA de la ISO igual al archivo adjunto y a ambas piernas A/B de repro-verify;
   registrar intentos y boot_id, sin tratar un success aislado como MATCH.
4. Evidencia QEMU versionada en main: comprobar que el fichero existe y nombra
   el SHA-256 completo de la ISO. Ya está versionada por #73 en repro/evidencia/2026-11-10-qemu-instalado-03ff84c.md
   (bloque NIMBO_APROBACION_QEMU). Su aprobación del
   environment es además la puerta humana; el fichero no la sustituye.
5. Tag y release inexistentes: cualquier colisión aborta, nunca sobrescribe.

## Jobs y permisos propuestos

- Validar: contents:read y actions:read; sin secretos. Checkout del código del
  workflow en main, nunca ejecutar scripts descargados del candidato.
- Firmar: environment release con aprobación de Juan José. Recibe solo la
  distribución ya validada y la vuelve a comprobar. Solo subclave de firma con caducidad; la primaria queda offline con Juan José.
  Secretos: RELEASE_GPG_SUBKEY, RELEASE_GPG_PASSPHRASE (si hace falta) y
  RELEASE_GPG_FINGERPRINT (huella primaria autorizada). Comprobar la vinculación
  de la subclave firmante y rechazar una primaria secreta utilizable. Acciones
  fijadas por SHA completo. Llavero temporal y limpieza al terminar, sin registrar
  secretos. Sin contents:write en este job.
- Borrador: contents:write solo aquí, sin clave privada. Crear prerelease draft con el tag apuntando al SHA candidato (03ff84c),
  nunca a la punta de main, y subir los cinco assets sin clobber. Conservar SHA, runs y notas de procedencia.
- Comprobar: descargar de nuevo los cinco assets del borrador y ejecutar el
  verificador con la huella fijada por el canal independiente. Una subida o
  descarga incompleta falla; el borrador permanece sin anunciarse como publicado.

La publicación final es manual tras revisar el borrador verificado. Concurrency
por tag sin cancel-in-progress para evitar firmas o subidas interrumpidas.
Ni pull_request_target ni secretos en jobs de PR; sin permisos de administración,
Pages u OIDC. Un rollback no borra evidencias ni reemplaza assets.

## Compuertas antes de operar con la clave real

Juan José decidió el 12-nov la política de ADR-015: rechazar siempre al
caducar la subclave, aunque la firma sea anterior; un solo UID sin correo;
primaria ed25519 solo para certificar, 2 años, y subclave ed25519 de firma,
1 año. La conducta estricta del verificador ya coincide con esa decisión.
La firma exige que el ADR figure como Aceptado en el checkout de main usado
por el workflow; la decisión comunicada no sustituye ese cambio versionado.
Faltan la huella pública real y la configuración de environment/secretos.
La evidencia QEMU de #73 ya está versionada; el workflow comprobará su bloque
NIMBO_APROBACION_QEMU contra el hash, SHA y runs indicados. R11-R14 se cubren con pruebas locales de compuertas: procedencia incorrecta,
QEMU ausente/ambiguo, colisiones de tag/release y subida o publicación incompleta.
Esto no sustituye una ejecución de Actions con environment y permisos reales.

## Cinco assets de rc1 y plan B

nimbo-v1.0.0-rc1-amd64.iso, PROCEDENCIA.json, release-key.asc, SHA256SUMS y
SHA256SUMS.asc. El manifiesto cubre ISO, procedencia y certificado público.

Si caduca cualquiera de los tres artifacts, re-ejecutar completos **los dos
runs originales**, build-iso 42850483095 y repro-verify 42850482997, usando
**Re-run all jobs**. No basta con reconstruir la ISO: hacen falta también los
artifacts nuevos de ambas piernas A/B. El rerun conserva el run ID y aumenta
run_attempt; se registran los intentos y los IDs nuevos de artifacts.

Exigir de nuevo el mismo hash
28760694ba8e20d13b98d04435d97937ae4e33ece521d62324c0ed33c484ae90.
Promover los runs/attempts aprobados con las mismas compuertas. artifact()
descarta los expired antes de contar: un vigente y uno caducado permite elegir
el vigente; dos vigentes del mismo nombre siguen siendo ambiguos y se rechazan.
No cambian las comprobaciones de run, digest ZIP, contenido y SHA/MATCH.
La copia local conservada no se presenta como un nuevo artifact de CI.

## Implementacion entregada

- validar: lee los runs y la evidencia de main; descarga cada artifact ZIP,
  exige el digest de la API y extrae solo nombres fijos, sin enlaces ni rutas
  externas. Exige SHA de la ISO igual al adjunto y a A/B, con boot_id distintos.
- firmar: requiere aprobación del environment y repite la validación completa
  después de aprobar. Los secretos se exponen solo al paso de firma. Rechaza
  clave primaria secreta utilizable, subclave sin caducidad vigente, revocada,
  ausente o ambigua. Selecciona por huella exacta de subclave y vuelve a verificar.
- borrador: recibe por ID el artifact publico del mismo run, verifica la firma,
  crea el tag exacto y prerelease draft sin sobrescribir, descarga sus cinco
  assets y vuelve a verificar. No hay paso de publicacion automatica.

La huella guardada como secreto no se pasa literalmente entre jobs: GitHub
puede bloquear outputs que coincidan con secretos. Se transmite su SHA-256 y
el job del borrador exige que la huella del certificado publico tenga ese hash;
ademas verifica la firma contra esa identidad completa. No se exportan claves
privadas a los artifacts. Todas las acciones estan fijadas por SHA completo.

Alcance inicial deliberado: solo v1.0.0-rc1 y 03ff84c con hash 28760694….
Otro candidato requiere revisar las constantes y su evidencia. Si caduca el
conjunto, reejecutar completos ambos runs originales que conservan evento
push/main y SHA, y promover los runs/attempts aprobados con el mismo hash; un build disparado
por workflow_dispatch no cumple la compuerta de evento push aprobada.

Si una operacion de escritura falla despues de crear el tag o el borrador,
se conserva ese estado incompleto para revision. Reejecutar falla por colision;
no borra ni reemplaza assets. Juan Jose decide como retirarlo o usar rc2.

## Validacion de esta entrega

36 pruebas locales pasan en Python 3.13/GnuPG 2.4.7, con identidades efimeras.
Incluyen una firma real con exportacion solo de subclave y rechazo de una
exportacion que contiene la primaria secreta. actionlint 1.7.12 acepta el YAML
(shellcheck no ejecutado). La bateria ampliada tambien paso en bookworm: 36 passed, 1 warning en 1.59 s
(ejecucion de Alejandro), Python 3.11.2-1+b1, pytest 7.2.1-2 y
GnuPG 2.2.40-1.1+deb12u2. El warning corresponde al ZIP con nombre duplicado
creado deliberadamente por una prueba negativa. Falta revisar el workflow en Actions. No se han usado claves reales ni creado tags.

Comprobacion real de solo lectura: promover.py validar paso con build
42850483095 y repro 42850482997. Se comprobaron digests ZIP de la API,
procedencia push/main, SHA, MATCH y bloque QEMU en main. El resultado validado
se conserva en ~/.cache/nimbo-release/candidato-validado-03ff84c/.

## Configuración obligatoria del environment

Antes de cualquier dispatch, Juan José configura `release` con las dos barreras:

- **Required reviewers:** Juan José (@Duque-Londono).
- **Deployment branches:** solo `main`.

El if github.ref == refs/heads/main del YAML no protege por sí solo los secretos:
workflow_dispatch desde otra rama usa el YAML de esa rama, que podría omitirlo.
La restricción de ramas del environment protege los secretos independientemente
del YAML. Sin ambas políticas el workflow no debe utilizarse con claves reales.
Su configuración corresponde a Juan José; este PR no modifica ajustes de GitHub.

## Ensayos previos propuestos por Juan José

1. Tras mergear #78 y configurar el environment: dispatch con valores por defecto.
   validar corre sin secretos en Actions; firmar queda esperando aprobación y
   Juan José **la rechaza**. Prueba de permisos, rutas y gh, sin firmar ni crear
   tag, borrador o release. Este ensayo aún no se ha ejecutado.
2. Plan B sin tocar el candidato: usar los runs de main del commit 3825b0e,
   build 42525558358 y repro 42525558338. Caducan el 15-nov hacia las 21:42 UTC.
   Registrar la expiración exacta de cada artifact; después de que caduquen,
   re-ejecutar **ambos completos (Re-run all jobs)** y llamar artifact() en
   lectura para la ISO y A/B, comprobando digests e IDs de los vigentes.
   Esa noche debe completarse el ensayo antes del lunes y comunicarse el resultado.
   No llamar validar ni cambiar sus constantes: ese comando solo acepta rc1/03ff84c.
   No re-ejecutar ahora ni tocar los runs candidatos. Ensayo futuro pendiente;
   los tests con API simulada no acreditan el comportamiento real tras caducar.

## Revision del plan B (#78)

Rojo: el caso con un artifact caducado y otro vigente del mismo nombre falla
con el filtro anterior (artifact ausente o ambiguo). Verde: tras excluir expired
antes de contar, pasa y descarga el ID del vigente; dos vigentes siguen fallando.
38 pruebas locales aprobadas en Python 3.13/GnuPG 2.4.7. Alejandro repitio la
bateria en bookworm: 38 passed, 1 warning en 1.53 s; Python 3.11.2-1+b1,
pytest 7.2.1-2 y GnuPG 2.2.40-1.1+deb12u2. El warning corresponde al ZIP
duplicado deliberado de la prueba negativa. El ensayo real tras caducar sigue
pendiente; no se ha re-ejecutado ningun run ni usado la clave real.

## Ventana sin merges durante los reruns

Los reruns de build 42850483095 y repro 42850482997, y el ensayo con los
runs de 3825b0e (42525558358 y 42525558338), conservan ref = refs/heads/main.
Comparten estos grupos con los builds disparados por pushes a main:

- build-iso-refs/heads/main.
- repro-verify-refs/heads/main-normal.

Ambos usan cancel-in-progress: true. Durante la ventana completa del rerun
(aproximadamente 12 minutos), coordinar con el equipo que **no se mergeen a
main cambios en iso/, packages/ ni security/hardening/3b2/** que recompilen
la ISO. Un push que active esos workflows puede cancelar el rerun. No basta
con que la peticion de reejecucion haya sido aceptada: comprobar despues que
el attempt nuevo de **ambos runs** termino en success, no en cancelled, antes
de comprobar y promover sus artifacts.

El repro-verify semanal (lunes a las 06:00 UTC) usa un grupo separado y no
choca con el grupo normal. Esta regla no modifica la concurrencia de CI;
es coordinacion operativa para el ensayo y el plan B.
