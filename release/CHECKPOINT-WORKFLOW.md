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
4. Evidencia QEMU vinculada al hash exacto y aprobación de Juan José.
   No hay una API que certifique la prueba humana: se registra y revisa como tal.
5. Tag y release inexistentes: cualquier colisión aborta, nunca sobrescribe.

## Jobs y permisos propuestos

- Validar: contents:read y actions:read; sin secretos. Checkout del código del
  workflow en main, nunca ejecutar scripts descargados del candidato.
- Firmar: environment release con aprobación de Juan José. Recibe solo la
  distribución ya validada y la vuelve a comprobar. Clave real configurada por
  Juan José; llavero temporal y limpieza al terminar. No registrar secretos.
- Borrador: contents:write solo aquí, sin clave privada. Crear prerelease draft
  y subir los cinco assets sin clobber. Conservar SHA, runs y notas de procedencia.
- Comprobar: descargar de nuevo los cinco assets del borrador y ejecutar el
  verificador con la huella fijada por el canal independiente. Una subida o
  descarga incompleta falla; el borrador permanece sin anunciarse como publicado.

La publicación final es manual tras revisar el borrador verificado. Concurrency
por tag sin cancel-in-progress para evitar firmas o subidas interrumpidas.
Ni pull_request_target ni secretos en jobs de PR; sin permisos de administración,
Pages u OIDC. Un rollback no borra evidencias ni reemplaza assets.

## Antes de implementar release.yml

Juan José debe confirmar este desglose de jobs, la aprobación QEMU asociada al
hash completo, la huella pública y los nombres de secretos/environment que
configurará. R11-R14 de procedencia, publicación incompleta y reejecución
se implementan y prueban con el workflow después del checkpoint.
