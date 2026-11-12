# Distribución firmada: preparación local

Estado: herramientas locales en desarrollo, sin workflow ni publicación.
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
README y documento de sustentación. Una clave descargada junto a la ISO no
establece por sí sola la confianza. El verificador usa un llavero temporal y
exige una sola identidad primaria; admite firmas de sus subclaves vinculadas.
No hereda el llavero del usuario ni busca claves en la red.

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
pequeño de prueba que no es una ISO arrancable. Las 15 pruebas locales pasaron
en Python 3.13 y GnuPG 2.4.7 de trixie; falta ejecutar en bookworm antes de cerrar.
No prueban publicación, permisos de Actions ni verificación de descargas de Releases.

## Correcciones

Nunca sobrescribir assets ni reutilizar un tag. Un candidato corregido usa rc2;
rc1 se marca retirado en sus notas. La herramienta no crea tags, Releases,
comentarios, secretos ni cambios en GitHub.

Para repetir en bookworm con el script existente del repositorio:

```sh
sudo env CONTAINER_ENGINE=docker ./ci/test-modulo-en-bookworm.sh release gnupg
```
