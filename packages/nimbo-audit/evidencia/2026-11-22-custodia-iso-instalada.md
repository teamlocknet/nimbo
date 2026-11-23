# Evidencia — `nimbo-audit` 0.2.0 en la ISO `v1.0.0` instalada

**Fecha:** 22-nov-2026 · **Ejecutó y verificó con los ojos:** Juan José · **Decisión:**
[ADR-021](../../../docs/adr/ADR-021-sellado-y-custodia-audit.md)

**Entorno:** copias de una instalación de la ISO `v1.0.0` en QEMU con Secure Boot y sin red. El
disco original no se modificó (mismo SHA-256 antes y después). La clave y su frase fueron solo de
prueba, la frase la tecleó Juan José y la clave se borró al terminar.

**Paquete:** `nimbo-audit_0.2.0-1_all.deb`, SHA-256
`ebcf8fab2f0a8597914286d208d885bf3ff4d3bb1671caa0a34efac44c66cb97`.

## Hallazgo

El primer intento falló: `gpg` y `gpg-agent` no están en el sistema instalado ni se pueden obtener
sin red. La sesión live los trae, pero el instalador los retira como huérfanos. El lote de 0.2.0
debe incluirlos.

## Paquetes añadidos al lote

Sus hashes coinciden con los índices del snapshot `20260901T000000Z`, cuya firma de Debian se
comprobó con `gpgv`.

| Paquete | Versión | SHA-256 |
|---|---|---|
| `gpg` | 2.2.40-1.1+deb12u2 | `5bb24757dc7206f42f419cc1309a4496d1e8ef2b1b539e095ad1c173ef6aa65d` |
| `gpg-agent` | 2.2.40-1.1+deb12u2 | `3f6b29302a0c0478358efb7e6d7b98e5a246db4287659494975423e482328caa` |
| `gpgconf` | 2.2.40-1.1+deb12u2 | `ce17a8b76468d3f4d6448efdeb5dab8a2613a9e0eb2c37f0987418a0d3ebd5a0` |
| `pinentry-curses` | 1.2.1-1 | `27b3d102545f597df9e6dc5c7f6590a648de09b57debd6b05ad3d1189de428d5` |
| `libassuan0` | 2.5.5-5 | `5912430927da16ccc831459679207fdbb9dfc5a206f2bab8d6f36d5a1ab53e25` |
| `libnpth0` | 1.6-3 | `43c90d45f7cf5584108964b919d6c728680d81af5fa70c8fb367d661cef54e8c` |

## Resultados

**Sello: 11 OK, 0 fallos.** Creación de clave con frase, `init`, `capture`, `report`, `verify`,
`seal` con frase, `verify` con ancla y huella, `capture` y `report` rechazados en el caso sellado,
y un ataque que reescribe evidencia e índice: `verify` lo detecta y marca `Sello: ROTO`.

**Lote en copia limpia: OK.** Con los mismos argumentos de `apt-get` que usa `nimbo-update-offline`,
`apt-get` termina con código 0, `dpkg --audit` queda vacío y `nimbo-audit` pasa de 0.1.0 a 0.2.0.

## Límites

- La prueba del sello se hizo en una copia donde 0.2.0 se instaló con `dpkg`, tras un primer
  intento a medias. La instalación con `apt` se probó aparte, en otra copia limpia.
- **No se probó el lote firmado** ni la verificación de su firma: necesita la clave de release.
- **No se volvió a medir el hermetismo con el lote aplicado.** `gpg-agent` habilita sockets de
  usuario. `dirmngr` no se instala.
- Es QEMU, no hardware real.
