# Construir y validar el paquete Debian

Ejecutar desde la ra?z del clon Linux, en Bash, con Docker disponible.
Las herramientas se instalan en contenedores desechables, desde el snapshot
bookworm/main del proyecto; no se instala nada mediante pip.

## Construcci?n

    sudo bash packages/nimbo-audit/build-deb.sh

El script monta el m?dulo como solo lectura y construye en una copia interna.
Imprime un directorio temporal de artefactos fuera del repositorio y guarda
el log, .deb, .buildinfo y .changes. Ejecuta dpkg-buildpackage -us -uc -b:
construcci?n binaria sin firma. El paquete fuente 3.0 (quilt) y su archivo
.orig.tar.gz no se han validado en este procedimiento.

Los scripts leen el digest de test-in-bookworm.sh y el timestamp de
iso/live-build/snapshot.env; no modifican la receta ni CI.
No usar NIMBO_BASE_IMAGE para sustituir la imagen en estas comprobaciones.

## Instalaci?n y lintian

Sustituir /ruta/artefactos por el directorio que imprimi? la construcci?n:

    sudo bash packages/nimbo-audit/test-deb.sh /ruta/artefactos
    sudo bash packages/nimbo-audit/lint-deb.sh /ruta/artefactos

La prueba instala el .deb en un contenedor limpio, sin montar el c?digo fuente.
Comprueba --help, la presencia del manual y su compresi?n con gzip -t.
La imagen m?nima excluye /usr/share/man/* durante la instalaci?n; la prueba
a?ade una excepci?n solo para este manual y sus directorios, dentro del
contenedor. Esto no cambia el paquete ni la configuraci?n del anfitri?n.

Lintian analiza el paquete binario. Criterio: ning?n E: y justificar los W:.
initial-upload-closes-no-bugs se admite porque el paquete propio no cierra
un bug de Debian. No se inventa un n?mero ni se oculta el aviso.

## Reproducibilidad

Construir dos veces sin modificar las entradas; conservar ambos directorios:

    sha256sum /ruta/build-A/nimbo-audit_0.1.0-1_all.deb /ruta/build-B/nimbo-audit_0.1.0-1_all.deb
    cmp /ruta/build-A/nimbo-audit_0.1.0-1_all.deb /ruta/build-B/nimbo-audit_0.1.0-1_all.deb

cmp devuelve 0 si son id?nticos. No regenerar el changelog entre builds.
Logs y binarios quedan fuera del repositorio. Revisar los logs antes de compartirlos.

## Evidencia y l?mites

ADR-010 registra las pruebas ejecutadas por Alejandro. Los tres scripts
de este directorio se ejecutaron correctamente: build-deb.sh obtuvo
50 passed y el mismo SHA-256 que los dos builds previos; test-deb.sh
completo la instalacion, --help y gzip -t del manual; lint-deb.sh
mostro solo initial-upload-closes-no-bugs, sin errores E:.

Artefactos de esta ejecucion: /tmp/nimbo-deb-build.0ezEtV.
SHA-256 del .deb:
e42d6f374cedaeb995b9d49d273e7c47f1c1a51219fe9eb6894bfd3bcf550c31

Los directorios /tmp son temporales: conservar los logs necesarios antes
de reiniciar o limpiar el sistema.

No se ha probado el paquete fuente ni reproducibilidad entre m?quinas.
CI roja/verde requiere checkpoint de Juan Jos? y sigue pendiente.
La integraci?n a la ISO corresponde a PR-B con checkpoint separado.
