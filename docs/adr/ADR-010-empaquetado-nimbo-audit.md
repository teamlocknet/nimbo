# ADR-010 — Empaquetado Debian de nimbo-audit

Estado: propuesto · Responsable: Alejandro

## Contexto

nimbo-audit 0.1.0 implementa init, capture y report. Sus 50 tests
pasaron en el contenedor bookworm anclado del proyecto, con Python 3.11
y dependencias desde APT. Todavía no tiene empaquetado Debian.

El paquete debe instalarse sin PyPI y usar dependencias de bookworm main.
La integración a la ISO corresponde a un PR posterior con checkpoint.

## Opciones

1. Debhelper y pybuild con el plugin pyproject: reutiliza pyproject.toml,
   setuptools y las herramientas de integración Python de Debian.
2. Copiar manualmente archivos y crear un lanzador: evita pybuild,
   pero duplica la configuración de instalación y requiere mantenerla.

## Decisión propuesta

Usar debhelper-compat (= 13), dh-python y pybuild-plugin-pyproject,
con setuptools como backend. Declarar explícitamente las dependencias
de construcción y pruebas necesarias desde APT.

Crear debian/ dentro de packages/nimbo-audit/. Proponer un paquete
Architecture: all, con el módulo nimbo_audit y el comando nimbo-audit.

Generar dependencias mediante ${python3:Depends} y ${misc:Depends},
comprobando que Typer quede declarado correctamente.
Pandoc será Suggests, no dependencia obligatoria.

Maintainer: Juan José Duque <jd1020157@gmail.com>.
Copyright: LockNet. Licencia: GPL-3.0-or-later.

## Cómo se verifica

- Construir en la imagen por digest y con el snapshot del proyecto.
- Ejecutar los 50 tests durante la construcción.
- Instalar el .deb en un contenedor bookworm limpio mediante APT
  y ejecutar nimbo-audit --help.
- Inspeccionar contenido y dependencias del paquete.
- Ejecutar lintian: sin errores E:; justificar los avisos restantes.
- Construir dos veces desde copias limpias con las mismas entradas
  y comparar los SHA-256 de los .deb.
- Incorporar el job de CI con evidencia roja y verde después del
  checkpoint de Juan José para modificar workflows.

## Consecuencias

El empaquetado reutiliza la configuración Python existente.
Se deberán verificar la traducción de dependencias y la ausencia de
metadatos variables entre construcciones.

La construcción, instalación y comparación de dos builds locales
están verificadas; la validación en CI sigue pendiente.
Este ADR no autoriza cambios en CI, receta de ISO, release, hardening o TPM.


## Resultados de validación local

Verificados mediante comandos ejecutados por Alejandro en Debian WSL2:

- Dos construcciones en contenedores separados ejecutaron los 50 tests
  correctamente y produjeron el mismo SHA-256 del paquete con manual:
  `e42d6f374cedaeb995b9d49d273e7c47f1c1a51219fe9eb6894bfd3bcf550c31`.
- Instalación con APT en un contenedor limpio: correcta; dependencias
  descargadas desde el snapshot bookworm/main.
- `nimbo-audit --help`: código de salida 0.
- Manual instalado: 584 bytes; `gzip -t` terminó correctamente.
  La prueba añadió una excepción local porque la imagen mínima excluye
  `/usr/share/man/*` mediante la configuración de dpkg.
- Lintian 2.116.3+deb12u1: sin errores E:.
  Único aviso: initial-upload-closes-no-bugs, justificado porque es
  un paquete propio y no corresponde cerrar un bug de Debian.

La comparación demuestra reproducibilidad en las dos ejecuciones locales;
no se ha comprobado entre máquinas distintas.

Pendientes: incorporar instrucciones reproducibles de construcción y
validación al repositorio; job de CI con checkpoint y evidencia roja/verde.
La integración a la ISO corresponde a PR-B.

## Fecha

2026-11-01

## Procedimiento incorporado al repositorio

Alejandro ejecuto build-deb.sh, test-deb.sh y lint-deb.sh sobre los
artefactos /tmp/nimbo-deb-build.0ezEtV: 50 tests correctos, mismo SHA-256
registrado arriba, ayuda y manual correctos, lintian sin E: y con el
unico aviso justificado. Ver packages/nimbo-audit/EMPAQUETADO.md.
