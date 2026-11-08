# repro/espejo — espejo parcial del snapshot anclado (ADR-016)

Servidor HTTP mínimo que sirve los ficheros del snapshot anclado de `snapshot.debian.org`
(`iso/live-build/snapshot.env`) desde un directorio local. Lo que no tiene, lo descarga una
vez, lo guarda **sin tocarlo** y lo sirve. apt y debootstrap siguen verificando la firma de
Debian y el hash de cada fichero: un fichero alterado en el espejo hace fallar el build.

Decisión y motivos: [ADR-016](../../docs/adr/ADR-016-espejo-parcial-snapshot.md).

## Uso en local

```
# terminal 1: el espejo (se queda escuchando en 127.0.0.1:8765)
python3 -I repro/espejo/espejo.py --dir ~/.cache/nimbo-espejo --registro /tmp/espejo.registro

# terminal 2: el build, descargando del espejo
cd iso/live-build
NIMBO_ESPEJO=http://127.0.0.1:8765 CONTAINER_ENGINE=docker ./build-in-container.sh
```

- Sin `NIMBO_ESPEJO`, el build descarga directo de `snapshot.debian.org`, como siempre.
- `--solo-cache`: no descarga nunca; lo que falte da 404. Sirve para demostrar que un build
  salió entero del espejo, sin red hacia el snapshot.
- `--registro`: una línea por petición (`CACHE`, `DESCARGA`, `NO-ENCONTRADO`, `RECHAZADA`,
  `ERROR`) con la ruta.
- Solo acepta `/archive/{debian,debian-security}/<snapshot>/…`. Como esas rutas son
  inmutables, lo guardado no caduca.

## En CI

`build-iso` y las dos piernas de `repro-verify` arrancan el espejo con
`ci-espejo.sh arrancar` y lo restauran/guardan con `actions/cache` (solo se guarda si hubo
descargas). El `repro-verify` **semanal** (lunes 06:00 UTC) compila la pierna B directo del
snapshot: si da MATCH, el espejo y el snapshot producen la misma ISO.

## Tests

```
python3 -I repro/espejo/test_espejo.py
```

Usan un snapshot falso en localhost (sin red). También corren en CI (`tests-build-scripts`).
