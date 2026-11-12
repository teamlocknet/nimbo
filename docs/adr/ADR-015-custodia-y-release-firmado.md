# ADR-015 — Custodia de la clave y distribución firmada

**Estado:** Propuesto. Juan José decide su paso a Aceptado.
**Responsable de implementación:** Alejandro. **Custodio de la clave:** Juan José.
**Alcance:** release firmado; el repositorio APT queda para una etapa posterior.

## Contexto

La distribución debe permitir verificar la identidad de firma y la integridad de
la ISO publicada. La firma no acredita por sí sola reproducibilidad, QEMU ni
procedencia. El candidato aprobado es v1.0.0-rc1 como prerelease, promoviendo
los bytes de CI del commit 03ff84cd1804908cbd1fd7cdb90c0e8c1734a5fa,
no la punta de main y sin reconstruir durante la firma.

## Decisión propuesta

### Custodia y caducidad

Juan José genera y custodia la clave primaria (maestra) fuera de línea.
Conserva aparte un certificado de revocación. Ni la clave maestra ni ese
certificado se suben al repositorio, a artifacts ni al environment de Actions.

Para CI exporta exclusivamente una subclave apta para firma con caducidad,
vinculada a la identidad primaria. Juan José define su vigencia y renovación;
no se inventan fechas, huellas ni identidades antes de generar la clave.
El desarrollo y las pruebas usan claves efímeras, nunca la identidad real.

El environment `release`, configurado por Juan José, exige su aprobación para
el job de firma y contiene:

- RELEASE_GPG_SUBKEY: solo el material secreto de la subclave de firma.
- RELEASE_GPG_PASSPHRASE: si esa subclave requiere una frase de paso.
- RELEASE_GPG_FINGERPRINT: huella primaria completa autorizada, en mayúsculas.

El workflow debe comprobar la identidad primaria y la vinculación de la subclave
firmante, su capacidad de firma y vigencia. Debe rechazar una importación que
contenga la clave primaria secreta utilizable o identidades adicionales.
No basta aceptar cualquier firma criptográficamente válida del llavero.
Se selecciona y registra la huella pública de la subclave que firma.
El llavero del job es temporal y se limpia al terminar, también ante errores.
No se imprimen secretos, passphrases ni comandos que expongan sus valores.

### Estados de firma y política de caducidad propuesta

Se acepta solo exactamente un GOODSIG y un VALIDSIG con la primaria autorizada.
Se rechazan REVKEYSIG, EXPKEYSIG, EXPSIG, BADSIG, ERRSIG y NO_PUBKEY;
también KEYEXPIRED, SIGEXPIRED y KEYREVOKED. La salida 0 de gpgv no basta:
puede emitir VALIDSIG incluso con una subclave revocada o caducada.

**Propuesta para decisión de Juan José:** rechazar siempre al caducar la subclave,
aunque la firma sea anterior. Es simple y falla cerrada; como coste, un release
antiguo deja de pasar la verificación normal cuando caduca su subclave.
Esta es la conducta provisional implementada hasta su decisión.

Alternativa que requiere otro diseño y pruebas: verificación histórica con aviso
explícito, solo para firmas anteriores a la caducidad y nunca con revocación.
No se implementa ahora ni se permite ignorar estados mediante una opción insegura.

### Confianza inicial y revocación

La huella primaria pública completa se publica en el README y en el documento
de sustentación como canal independiente. La clave pública incluida en el
release debe coincidir con esa huella; descargar ambos del mismo lugar no
establece por sí solo la confianza inicial.

El verificador ofrece `--clave <ruta>` para aportar el certificado público vigente
obtenido por el canal independiente (README/repo), manteniendo la misma huella
primaria autorizada. Importa tanto ese certificado como el adjunto al llavero
aislado para conservar cualquier revocación conocida. Sin un certificado actualizado
no se pueden conocer revocaciones posteriores: un atacante con una subclave
robada podría adjuntar el certificado antiguo sin revocar. Se recomienda una
caducidad corta, cuyo plazo decide Juan José; limita la ventana pero no sustituye
la actualización del certificado.

Ante compromiso, pérdida o caducidad, Juan José deshabilita el uso de la
subclave en CI y comunica la revocación o sustitución por los canales anteriores.
No se sobrescriben firmas ni evidencias de versiones publicadas. La rotación de
subclave y cualquier cambio de identidad primaria quedan documentados para
que quien verifica pueda identificar la clave vigente y las retiradas.

### Procedencia y puerta humana

Antes de firmar, el workflow comprueba en el repositorio fijo teamlocknet/nimbo:

1. Build de build-iso.yml lanzado por push a main, finalizado en verde, con
   head_sha igual al SHA completo indicado por el operador.
2. Run de repro-verify.yml sobre el mismo SHA con las piernas A y B disponibles
   y sus hashes iguales; los bytes de la ISO descargada dan ese mismo hash.
3. Evidencia QEMU versionada en main que existe y nombra el SHA-256 completo
   de esa ISO. La salida redactada ya está versionada por #73:
   repro/evidencia/2026-11-10-qemu-instalado-03ff84c.md, bloque
   NIMBO_APROBACION_QEMU. Se cita por enlace blob fijado al commit
   b4d41e4c965c7c33b9871a314359164e96ea9e23; el workflow verifica además
   que el fichero existe en main y que el bloque nombra el hash esperado.
   Su aprobación del environment constituye además la puerta humana.

Los candidatos/run se indican expresamente: no se elige el último artifact.
El tag apunta al commit promovido, no al commit del workflow en main.
El código del workflow procede de main revisado, nunca del artifact o de un PR.
Las acciones del job que firma quedan fijadas por SHA completo, no por etiqueta.

### Archivos publicados y permisos

Para rc1 se publican exactamente cinco archivos:

1. nimbo-v1.0.0-rc1-amd64.iso.
2. PROCEDENCIA.json: commit, runs, snapshot, epoch, imagen base y hashes de
   ISO, ambas piernas y QEMU, con enlace de evidencia.
3. release-key.asc: certificado público de la identidad autorizada, con subclaves.
4. SHA256SUMS: manifiesto de los tres archivos anteriores.
5. SHA256SUMS.asc: firma OpenPGP separada del manifiesto.

contents:write se limita al job que crea el borrador y sube sus assets, sin
clave privada. El job de firma no necesita escritura al repositorio. Se usa
workflow_dispatch desde main, sin pull_request_target ni permisos administrativos.
El borrador se descarga de nuevo y se verifica antes de publicarlo manualmente
como prerelease. Si falla una subida, descarga o verificación, no se anuncia
publicación correcta.

Si el tag o el release ya existen, se falla sin sobrescribir. Las correcciones
usan rc2 y marcan rc1 como retirado en sus notas. No se borran evidencias.

### Candidato inicial y caducidad del artifact

- Commit: 03ff84cd1804908cbd1fd7cdb90c0e8c1734a5fa.
- Build run: 42850483095; repro run: 42850482997.
- ISO SHA-256: 28760694ba8e20d13b98d04435d97937ae4e33ece521d62324c0ed33c484ae90.
- Artifact de build: caduca el 17-nov-2026 a las 16:11:17 UTC.

Si caduca, el plan B aprobado es recompilar ese mismo commit en CI,
comprobar el mismo hash 28760694…, repetir las comprobaciones de procedencia y
promover el nuevo run explícito. No se sustituye por una compilación de main
ni se publica una ISO local como si fuera el artifact de CI aprobado.

## Verificación

Las herramientas de release deben pasar en bookworm: caso íntegro, ISO y
manifiesto alterados, firma truncada o ausente, identidad incorrecta, subclave
vinculada, archivo ausente/no listado, rutas externas, duplicados y colisiones.
La verificación local no sustituye las pruebas del workflow: SHA/run incorrectos,
evidencia QEMU ausente o con otro hash, tag/release existente y publicación
incompleta. La descarga y verificación final las confirma otra persona con la
huella obtenida por el canal independiente.

## Consecuencias y pendientes

La clave primaria queda fuera de CI y el secreto operativo tiene caducidad.
La puerta humana y el manifiesto vinculan la promoción a bytes y evidencias
concretos. Sigue siendo necesario custodiar y renovar la subclave y comunicar
revocaciones; una firma no convierte software vulnerable en software seguro.

Pendientes de Juan José: generar la identidad, comunicar su huella pública,
configurar environment/secretos y decidir la política de caducidad.
La evidencia QEMU redactada ya está versionada por #73.
No se publica una huella de ejemplo como identidad real. Este ADR no configura
un repositorio APT, claves reales ni workflows; esos cambios requieren su revisión.
