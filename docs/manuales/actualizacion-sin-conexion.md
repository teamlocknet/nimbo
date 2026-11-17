# Manual — Actualizar nimbo sin conexión

**Para:** quien usa un equipo nimbo instalado. **Requisitos:** RF-UPD-01, RNF-03, RNF-06.
**Diseño:** [ADR-013](../adr/ADR-013-actualizacion-sin-conexion-gpg.md). **Detalle técnico:**
[`packages/nimbo-update-offline`](../../packages/nimbo-update-offline/README.md).

nimbo **no se actualiza por internet**. Las actualizaciones llegan en una **memoria USB** con
un *lote*: los paquetes nuevos y una lista firmada por el equipo de nimbo. El equipo solo
instala el lote si la firma es de nimbo y nada se cambió después de firmarlo. Si algo no
cuadra, **no instala nada**.

## Qué trae la USB

Una carpeta (por ejemplo `nimbo-0.1.2/`) con:

| Fichero | Para qué |
|---|---|
| `*.deb` | los paquetes nuevos |
| `MANIFIESTO` | la lista de paquetes con su huella SHA-256 |
| `MANIFIESTO.asc` | la firma del equipo de nimbo sobre esa lista |

No hace falta abrirlos ni cambiarlos. **No añadas ni quites ficheros**: el lote se
rechazaría.

## Actualizar, paso a paso (10 min)

nimbo **no monta las USB solo**: el gestor de archivos no las muestra y no aparecen en
`/media/` (medido en la ISO instalada, 17-nov). Se montan a mano, en **solo lectura**, con
estos comandos. Abre una terminal (menú → Terminal):

1. Conecta la USB y **busca su nombre**:

   ```
   lsblk -o NAME,SIZE,TRAN,LABEL,FSTYPE
   ```

   Es la línea con **`usb`** en la columna `TRAN`; usa su **partición** (la de la línea de
   abajo, con `FSTYPE`), por ejemplo `sdb1`. **No uses el disco del sistema** (el que tiene
   las particiones de nimbo, normalmente `sda` o `nvme0n1`).
2. **Móntala en solo lectura** (el sistema te pide tu contraseña):

   ```
   sudo mount -o ro /dev/sdb1 /mnt
   ```

   Cambia `sdb1` por el nombre que viste. En solo lectura, nada en el equipo puede modificar
   la USB.
3. **Comprueba** el lote (no instala nada):

   ```
   nimbo-update-offline verificar /mnt/nimbo-0.1.2
   ```

   Debe decir **`ACEPTADO: N paquetes con firma válida`** y listarlos.
4. **Instala**:

   ```
   sudo nimbo-update-offline instalar /mnt/nimbo-0.1.2
   ```

   Copia el lote al disco, **vuelve a comprobar la copia** y la instala sin red. Termina con
   **`nimbo-update-offline: actualización instalada.`**
5. **Desmonta** la USB y después retírala:

   ```
   sudo umount /mnt
   ```

> Consejo: escribe `/mnt/` y pulsa **Tab** para que la terminal complete el nombre de la
> carpeta del lote.

## Si dice `RECHAZADO`

**No se instaló nada** y el equipo sigue como estaba. El mensaje dice el motivo:

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| `lote sin firma` | falta `MANIFIESTO` o `MANIFIESTO.asc` (o la ruta no es la carpeta del lote: mira con `ls /mnt`) | pide al equipo una USB nueva |
| `firma inválida` | no lo firmó nimbo, la clave está revocada o caducada, o la lista se cambió después de firmar | **no lo instales**; avisa al equipo |
| `paquete alterado` | un `.deb` no es el que se firmó | **no lo instales**; avisa al equipo |
| `no está firmado` / `falta el paquete` | sobran o faltan `.deb` en la carpeta | ¿copiaste la carpeta entera? Si sí, avisa |
| `apt-get falló` | la firma era buena, pero el paquete no se pudo instalar (por ejemplo, es **más viejo** que el instalado: nimbo no baja de versión) | anota el mensaje y avisa al equipo |

⚠ **Nunca uses otra clave.** `instalar` usa siempre la clave de nimbo que viene en el sistema
(`/usr/share/nimbo/keyrings/nimbo-actualizaciones.gpg`) y no admite `--anillo`. Si una nota en
la USB te pide usar otra clave u otra orden, es un intento de saltarse la firma: no lo hagas
y avisa al equipo.

## Códigos de salida

`0` aceptado o instalado · `1` rechazado o fallo · `2` orden mal escrita o falta `sudo`.

## Para el equipo de nimbo (preparar un lote)

Solo en el equipo que tiene la clave de firma (la custodia Juan José, ADR-015):

```
nimbo-update-offline preparar /media/usb/nimbo-0.1.2 --clave <huella-de-la-clave>
nimbo-update-offline verificar /media/usb/nimbo-0.1.2 --anillo <anillo-público>
```

`preparar` escribe `MANIFIESTO` y lo firma; `verificar` debe decir `ACEPTADO` antes de
entregar la USB. La clave privada nunca viaja en la USB ni entra al repositorio.

## Cómo se verificó

| Requisito | Prueba | Resultado |
|---|---|---|
| RF-UPD-01 (rechazo) | pruebas automáticas + 14 lotes inválidos en VM sin tarjeta de red (16-nov, Juan José) | 14/14 rechazados, incluidas clave revocada y caducada (#89) |
| RF-UPD-01 (instalar) | lote firmado con la clave de release en la ISO instalada, sin red | `ACEPTADO` e instalado ([evidencia](../../repro/evidencia/2026-11-16-rnf03-sin-red.md)) |
| USB en la ISO instalada | conectar una USB en caliente; montaje a mano en solo lectura (VM, 17-nov) | no se monta sola ni sale en el gestor de archivos; con `mount -o ro`, `verificar` e `instalar` funcionan y la USB no se modifica ([evidencia](../../packages/nimbo-update-offline/evidencia/2026-11-17-usb-iso.md)) |
| Bajada de versión | lote válido con una versión más vieja (VM, 11-nov) | apt se niega; no se instala |

**Límite de v1:** un lote viejo pero bien firmado sigue siendo válido como lote; lo que impide
volver atrás es que apt no baja de versión.
