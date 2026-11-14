# Distribución firmada: preparación local

Estado: herramientas locales verificadas y workflow preparado para revision;
sin ejecucion de firma real ni publicacion.
Requiere Python 3.11+, GnuPG (`gpg` y `gpgv`). No instala paquetes ni configura
claves reales. Juan José custodia y configura la identidad real de firma.

## Contrato

Se distribuyen exactamente cinco archivos:

- nimbo-vX.Y.Z-rcN-amd64.iso
- PROCEDENCIA.json
- release-key.asc
- SHA256SUMS (cubre los tres anteriores)
- SHA256SUMS.asc (firma separada del manifiesto)

La huella primaria completa se obtiene por el canal independiente acordado:
README y documento de sustentación. Clave vigente, generada el 13-nov-2026:

- Huella primaria: `0C50 B739 1A9B 8CFF 8A36  A627 D3B9 111F EC57 48C6`
- Certificado público para `--clave`: `release/nimbo-release-publica.asc`

Una clave descargada junto a la ISO no establece por sí sola la confianza. El
verificador usa un llavero temporal y exige una sola identidad primaria; admite
firmas de sus subclaves vinculadas. No hereda el llavero del usuario ni busca
claves en la red.

PROCEDENCIA.json tiene: tag prerelease; commit completo; build_run; repro_run;
iso_sha256; leg_a_sha256; leg_b_sha256; qemu_iso_sha256; qemu_evidence_url;
snapshot; source_date_epoch; base_image_digest. Los cuatro hashes deben ser
iguales. La herramienta comprueba coherencia, **no autentica por sí sola la
procedencia en GitHub ni convierte una afirmación QEMU en prueba**. Esa compuerta
corresponde al workflow y a la aprobación humana del candidato exacto.

## Uso

Primero preparar con la ISO ya construida, candidato revisado y clave pública:

```sh
python3 release/release.py preparar --iso /ruta/candidato.iso \
  --candidato /ruta/candidato.json --clave-publica /ruta/publica.asc \
  --salida /ruta/nueva-distribucion --huella HUELLA_PRIMARIA_COMPLETA
```

La salida debe ser nueva. No se sobrescribe ni se reutiliza una preparación
incompleta. Después, en el entorno de firma autorizado, firmar SHA256SUMS con
GPG y generar SHA256SUMS.asc (firma ASCII separada). No reconstruir la ISO.
La importación y custodia de la clave real no forman parte de este programa.

```sh
python3 release/release.py verificar /ruta/nueva-distribucion \
  --huella HUELLA_PRIMARIA_COMPLETA
python3 -m unittest discover -s release/tests -v
```

Las pruebas generan dos identidades efímeras en un directorio temporal,
eliminan su llavero y no imprimen ni versionan material privado. Usan un archivo
pequeño de prueba que no es una ISO arrancable. Las 15 pruebas pasaron localmente en Python 3.13/GnuPG 2.4.7 y en el
contenedor bookworm anclado: Python 3.11.2-1+b1, pytest 7.2.1-2 y
GnuPG 2.2.40-1.1+deb12u2 (15 passed en 0.73 s, ejecución de Alejandro).
No prueban publicación, permisos de Actions ni verificación de descargas de Releases.

## Correcciones

Nunca sobrescribir assets ni reutilizar un tag. Un candidato corregido usa rc2;
rc1 se marca retirado en sus notas. La herramienta no crea tags, Releases,
comentarios, secretos ni cambios en GitHub.

Para repetir en bookworm con el script existente del repositorio:

```sh
sudo env CONTAINER_ENGINE=docker ./ci/test-modulo-en-bookworm.sh release gnupg
```

## Revisión de estados, revocación y certificado externo

Solo se acepta exactamente un GOODSIG y un VALIDSIG con la huella primaria
autorizada. Se rechazan REVKEYSIG, EXPKEYSIG, EXPSIG, BADSIG, ERRSIG y NO_PUBKEY,
así como avisos KEYEXPIRED, SIGEXPIRED o KEYREVOKED. Un código 0 de gpgv no basta.
El certificado debe contener una sola clave primaria autorizada y un solo UID.

Política decidida por Juan José el 12-nov (ADR-015): rechazar siempre una
subclave caducada, aunque la firma sea anterior. Una distribución antigua deja
de verificar al caducar. Una sola UID sin correo; primaria ed25519 solo para
certificar, 2 años; subclave de firma ed25519, 1 año. Juan José genera y
configura el material real fuera del repositorio.

La revocación solo se conoce si se dispone de un certificado actualizado.
Un atacante con una subclave robada puede adjuntar un certificado anterior.
Obtén el certificado vigente por el canal independiente y usa:

```sh
python3 release/release.py verificar /ruta/distribucion \
  --huella HUELLA_PRIMARIA_COMPLETA --clave /ruta/certificado-actualizado.asc
```

Se valida la huella tanto del certificado incluido como del externo y se importan
ambos al llavero aislado: no se descarta una revocación conocida en ninguno de
ellos. No se descargan claves automáticamente. Sin --clave se usa solo el adjunto;
ese modo no garantiza conocer revocaciones posteriores. Mantener la subclave
con caducidad corta limita esa ventana, sin sustituir la actualización.

Revisión local: dos reproducciones en rojo (revocación y caducidad) con el
verificador anterior; tras el arreglo, 21 pruebas aprobadas en trixie.
La batería ampliada también pasó en el contenedor bookworm anclado, ejecutada
por Alejandro: 21 passed en 1.40 s, Python 3.11.2-1+b1, pytest 7.2.1-2 y
GnuPG 2.2.40-1.1+deb12u2. Comando: ci/test-modulo-en-bookworm.sh release gnupg.

La evidencia QEMU ya está versionada en repro/evidencia/2026-11-10-qemu-instalado-03ff84c.md,
con bloque NIMBO_APROBACION_QEMU. CANDIDATO-VERIFICADO.json contiene el enlace
blob fijado al commit que la incorpora; no depende del texto mutable de un PR.

## Operacion del workflow

release.yml usa promover.py (procedencia y borrador) y firmar.py (subclave).
El codigo ejecutado se fija al SHA de main desde el que se hace dispatch;
el tag se crea sobre el commit candidato, no sobre ese main.
Ver CHECKPOINT-WORKFLOW.md para permisos, acciones fijadas por SHA, compuertas
y comportamiento ante fallos. No ejecutar el dispatch hasta que ADR-015 figure como Aceptado en main y
Juan José configure la subclave vigente, la huella pública y las dos políticas
del environment descritas abajo.

La bateria completa se ejecuta con el mismo comando bookworm anterior; ahora
incluye 36 casos. Los tests de GitHub usan dobles controlados y no publican nada.
La firma integrada de prueba usa claves efimeras y no instala una identidad real.

Validacion de la bateria ampliada en bookworm (ejecutada por Alejandro):
36 passed, 1 warning en 1.59 s. El warning de zipfile corresponde al archivo
con nombre duplicado creado deliberadamente por la prueba negativa; la
extraccion lo rechaza como se espera. Python 3.11.2, pytest 7.2.1 y GnuPG 2.2.40.

## Precondiciones del environment y plan B

Juan José configura `release` con **Required reviewers = Juan José** y
**Deployment branches = solo main** antes de usar claves reales. Ambas son
obligatorias. El if de main en el YAML no basta: un dispatch desde otra rama
usa su propio YAML y podría omitir esa condición. La política del environment
impide que esa rama acceda a los secretos. Este PR no configura esos ajustes.

El límite del candidato es **17-nov-2026, 16:11:04 UTC** (iso-sha-B), no la
caducidad de la ISO a las 16:11:17. El plan B re-ejecuta **los dos runs completos**,
build-iso 42850483095 y repro-verify 42850482997, con Re-run all jobs, para
renovar ISO y A/B. Se exige el mismo hash aprobado. Ver CHECKPOINT-WORKFLOW.md
para los ensayos propuestos en Actions y sobre los runs de 3825b0e.

Revision del plan B: 38 pruebas aprobadas en bookworm (ejecucion de Alejandro),
38 passed, 1 warning en 1.53 s. El warning es el ZIP duplicado deliberado de
la prueba negativa. El ensayo de reruns tras caducidad sigue pendiente.
