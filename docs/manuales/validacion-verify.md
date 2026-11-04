# A5: evidencia y procedimiento de validacion de verify

Requisito RF-AUD-04 / HU-13, plan del equipo v1.1. Rama:
alejandro/verify-integridad, creada desde main 4ca3801 (merge de PR #32).

## Rojo observado antes de implementar

Comando ejecutado por Alejandro en Debian WSL:

    sudo env CONTAINER_ENGINE=docker ./packages/nimbo-audit/test-in-bookworm.sh

Imagen: debian por digest 88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171.
Snapshot: 20260901T000000Z.
Python 3.11.2, click 8.1.3-2, pytest 7.2.1-2 y typer 0.7.0-1 desde APT.
Salida compartida por Alejandro el 3-nov-2026:

    collected 51 items
    FAILED tests/test_verify.py::test_verify_caso_integro
    assert 2 == 0
    1 failed, 50 passed in 0.31s

El comando verify no estaba registrado. El test se conservo antes del codigo
en el commit local d2a922d. Este rojo es local; no es un run rojo de GitHub CI.

## Verde y regresiones

Verde ejecutado por Alejandro el 3-nov-2026 con el mismo comando, imagen,
snapshot y versiones APT del rojo:

    collected 95 items
    tests/test_capture.py .............
    tests/test_init.py ...................
    tests/test_report.py ..................
    tests/test_verify.py .............................................
    95 passed in 0.72s

Son 50 pruebas previas y 45 casos nuevos. Una ejecucion intermedia dio
94 passed, 1 failed: el test de permiso denegado interceptaba Path.open,
pero el hashing usa builtins.open. Se corrigio la simulacion y se repitio
la suite completa con el resultado verde anterior. El CLI maneja el error
de lectura con mensaje limpio y salida 1.

Las pruebas nuevas deben cubrir:
- Caso integro, ruta explicita/relativa y caso activo.
- Un byte alterado, evidencia borrada, hash mal formado y resumen con otra
  evidencia intacta, nombrando la afectada.
- Estructura/version/JSON de indice invalidos; indice ausente y vacio.
- Rutas externas y enlaces que salen del caso, duplicados y errores de lectura.
- Manifiesto del caso igual antes/despues: rutas, tipos, permisos, mtime y hashes
  de archivos. No incluir atime, que puede cambiar como efecto de lectura.
- Report antes y despues con el mismo contenido; conservar los 50 tests previos.

## Limites

Solo valida la evidencia registrada contra un indice no firmado. Reescribir
ambos puede evadir la deteccion. No prueba autenticidad, ni cambios concurrentes,
ni las garantias globales de RAM/hermetismo/reproducibilidad de la ISO.
CI y receta de ISO no se modifican en A5. Integracion de esta version y pruebas
del paquete instalado quedan por verificar; no reutilizar hashes de PR-A para
afirmar reproducibilidad de este nuevo codigo.
