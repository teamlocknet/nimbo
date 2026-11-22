# Preparación de RF-DIST-01 final — todavía sin validación

Carpeta abierta el 18-nov-2026. **No contiene una aceptación de v1.0.0.**
Al preparar, la API de GitHub devolvió 404 para refs/tags/v1.0.0.
Juan José crea ese tag después de medir los arreglos #101–#103 en una ISO.
No se sustituye el candidato de main del 16-nov por una supuesta versión final.

La VM se prepara desde un overlay nuevo de Debian Bookworm, sin los cinco
módulos, fuente APT de nimbo ni certificado de release instalado. Solo se
instalan herramientas de validación. El disco y su socket de control quedan
en la caché privada del host, fuera del repositorio. PREPARACION-VM.json
registra la comprobación real de ese estado; no es evidencia de instalación.

## Cuando Juan José anuncie el tag

1. Resolver refs/tags/v1.0.0 al commit completo, incluyendo el destino de un
   tag anotado si lo hubiera. Registrar la respuesta y el commit.
2. Ejecutar desde main el workflow aprobado:

   `gh workflow run apt-repo.yml --repo teamlocknet/nimbo --ref main -f modo=v1.0.0 -F publicar=true`

   Registrar run/attempt y avisar a Juan José cuando firmar espere su aprobación.
   La aprobación de release le corresponde a él.
3. Esperar al despliegue correcto y arrancar la VM preparada. Antes de añadir
   la fuente, comprobar otra vez que no hay módulos, fuente ni clave nimbo.
4. Obtener por el canal independiente el certificado público y comprobar la
   primaria 0C50B7391A9B8CFF8A36A627D3B9111FEC5748C6. Guardar bytes y hash.
5. Contra https://teamlocknet.github.io/nimbo/apt/: verificar InRelease y
   Release.gpg con la política compartida de release/, igualdad InRelease/Release
   y hashes firmados antes de interpretar PROCEDENCIA.json. Comprobar Date y
   Valid-Until (30 días), candidate=false, release_tag=v1.0.0 y commit del tag.
   Si aún sirve el candidato anterior, parar sin instalar ni aceptar.
6. Leer las versiones y hashes del tag/publicación comprobada; ejecutar APT
   update, download e install con las CINCO versiones exactas. Guardar salidas,
   códigos, procedencia de APT, hashes descargados y dpkg-query instalado.
7. En ESA misma VM, desde el checkout del tag y sin alterar sus tests:

   `python3 -m unittest discover -s apt-repo/tests -p test_apt_transport.py -v`

   Exigir control positivo y rechazo de InRelease alterado, deb alterado y
   clave incorrecta. Guardar stdout, stderr y código de salida.
8. Recoger los archivos indicados en CHECKLIST.md, redactar resultados y generar
   SHA256SUMS. La fecha de ejecución será la real; ajustar la carpeta si el
   ensayo final se hace otro día. No exportar discos ni claves privadas.
9. Solo si todo pasa, abrir el PR de evidencia y sustituir los pendientes por
   el resultado en apt-repo/README.md y CHECKPOINT-WORKFLOW.md.
   Juan José revisa, acepta y mergea. No marcar RF-DIST-01 cerrado antes.

## Fuera de esta preparación

La mejora de firma del índice/reporte de nimbo-audit queda para después del APT.
No se cambia la ISO, ningún workflow, el sitio Pages ni la clave de release.
Si la sustentación queda después de Valid-Until, renovar con aprobación de
Juan José; no desactivar la comprobación de caducidad.

## Preparación completada

La VM completó el aprovisionamiento y se apagó normalmente. Se comprobó la
lista de snapshots: lista-sin-clave-nimbo. PREPARACION-VM.json confirma los
cinco módulos ausentes, sin fuente nimbo y sin su huella en los llaveros APT
revisados. VM-HOST.json identifica la preparación, sin incluir el disco.

El aprovisionamiento solo instala herramientas. qemu-guest-agent es
instrumentación de esta VM de laboratorio, accesible mediante un socket Unix
en un directorio privado del host; no es un servicio del producto. NoCloud se
desactiva tras aprovisionar para no repetir el script en el arranque final.
El servidor HTTP auxiliar se cerró. El siguiente arranque queda preparado en
la caché privada, sin instalar aún la clave ni la fuente de nimbo.

SHA256SUMS-PREPARACION cubre estos archivos de preparación. No sustituye el
manifiesto ni las salidas que se recogerán al validar el tag final.
