# Checkpoint pendiente: workflow del release firmado

Este documento concreta el diseño aprobado el 10-nov. No se ha creado ni
modificado .github/workflows/release.yml. Juan José revisa los cambios en CI.

## Entrada y compuertas

workflow_dispatch desde refs/heads/main, con tag, SHA completo, build_run y
repro_run explícitos. Primer candidato aprobado: v1.0.0-rc1,
03ff84cd1804908cbd1fd7cdb90c0e8c1734a5fa, build 42850483095,
repro 42850482997. La consulta del 11-nov confirma main/push/success y las
rutas build-iso.yml y repro-verify.yml para ese SHA. Artifact ISO:
13781341509, nimbo-iso-03ff84c, caduca 17-nov a las 16:11:17 UTC.

Antes de firmar, consultar la API del repositorio fijo teamlocknet/nimbo:

1. Ambos runs finalizados con success, SHA exacto, main y origen permitido;
   comprobar ruta/identidad del workflow. No aceptar PRs ni repos externos.
2. Artifact exacto del run, no caducado; descargar y cotejar su digest de archivo
   con la API antes de extraer. Rechazar rutas externas, enlaces y archivos extra.
3. SHA de la ISO igual al archivo adjunto y a ambas piernas A/B de repro-verify;
   registrar intentos y boot_id, sin tratar un success aislado como MATCH.
4. Evidencia QEMU versionada en main: comprobar que el fichero existe y nombra
   el SHA-256 completo de la ISO. Juan José la sube redactada. Su aprobación del
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

## Antes de implementar release.yml

El desglose está aprobado con las condiciones de Juan José. Primero se revisa
y cierra ADR-015 (Propuesto); después se prepara release.yml en un PR aparte.
Faltan la huella pública real, su configuración de environment/secretos y la
evidencia QEMU versionada por Juan José. R11-R14 de procedencia, publicación incompleta y reejecución
se implementan y prueban con el workflow después del checkpoint.

## Cinco assets de rc1 y plan B

nimbo-v1.0.0-rc1-amd64.iso, PROCEDENCIA.json, release-key.asc, SHA256SUMS y
SHA256SUMS.asc. El manifiesto cubre ISO, procedencia y certificado público.

Si caduca el artifact, recompilar 03ff84c en CI y exigir de nuevo el mismo hash
28760694ba8e20d13b98d04435d97937ae4e33ece521d62324c0ed33c484ae90.
Promover el nuevo run explícito con las mismas compuertas. La copia local
conservada no se presenta como un nuevo artifact de CI.
