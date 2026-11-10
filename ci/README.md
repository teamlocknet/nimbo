# ci

Scripts y utilidades de integración continua compartidos por los workflows.

**Dueño:** Juan José

| Script | Qué hace | Lo usa |
|---|---|---|
| `test-modulo-en-bookworm.sh <paquete> [apt...]` | Corre el `pytest` de un módulo Python con el Python 3.11 de bookworm y las dependencias desde APT del snapshot anclado, en el mismo contenedor que la ISO. La imagen y el snapshot se leen de la receta (`iso/live-build/`), sin copias | `ci.yml`, job `tests-modulos-bookworm` (`nimbo-nav`, `nimbo-update-offline`) |

En local: `CONTAINER_ENGINE=docker ci/test-modulo-en-bookworm.sh packages/nimbo-update-offline gnupg` (por defecto usa `podman`).
