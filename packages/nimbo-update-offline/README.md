# packages/nimbo-update-offline — actualización sin conexión

Implementa el [ADR-013](../../docs/adr/ADR-013-actualizacion-sin-conexion-gpg.md) para
**RF-UPD-01 / HU-14**: "el sistema rechaza el 100 % de los paquetes con firma inválida".
**Autor:** Emmanuel (`@Cardozo-Mosquera`). **Aceptación de RF-UPD-01** (prueba sin red,
integración): Juan José, dentro de la batería de RNF-03 (decisión del 10-nov).

## El lote de actualización

Un directorio (normalmente en una USB) con:

```
nimbo-audit_0.1.1-1_all.deb
nimbo-nav_0.1.1-1_all.deb
MANIFIESTO          # "<sha256>  <nombre.deb>" por línea
MANIFIESTO.asc      # firma GPG separada del MANIFIESTO
```

Se acepta **solo** si: la firma es válida para el anillo de nimbo
(`/usr/share/nimbo/keyrings/nimbo-actualizaciones.gpg`); el manifiesto no está vacío ni
repite nombres; cada nombre es un `.deb` sin rutas; los `.deb` del directorio son
exactamente los del manifiesto; y cada SHA-256 coincide.

## Procedimiento por USB, paso a paso

**En el equipo de firma** (con la clave de actualizaciones; la custodia Juan José):

1. Copia los `.deb` de la versión nueva a una carpeta de la USB, por ejemplo `/media/usb/nimbo-0.1.1/`.
2. `nimbo-update-offline preparar /media/usb/nimbo-0.1.1 --clave <huella-de-la-clave>`.
   Escribe `MANIFIESTO` y lo firma (`MANIFIESTO.asc`).
3. `nimbo-update-offline verificar /media/usb/nimbo-0.1.1 --anillo <anillo-público>`. Debe decir `ACEPTADO`.
4. Expulsa la USB.

**En el equipo nimbo, sin red:**

1. Conecta la USB y monta la partición (en Xfce aparece en el gestor de archivos).
2. `nimbo-update-offline verificar /media/<usuario>/<usb>/nimbo-0.1.1` → `ACEPTADO` y la lista de paquetes.
3. `sudo nimbo-update-offline instalar /media/<usuario>/<usb>/nimbo-0.1.1`.
   Copia el lote a un directorio propio, **verifica la copia** (así nadie puede cambiar la
   USB entre la verificación y la instalación) e instala con `apt-get --no-download`.
4. Si dice `RECHAZADO`, **no se instaló nada**. Anota el motivo y avisa al equipo.

⚠ `instalar` usa **siempre** el anillo de nimbo y **no admite `--anillo`**. Si un lote o una
nota en la USB te pide usar otra clave, es un intento de saltarse la firma: no lo hagas.
`verificar --anillo` existe solo para diagnosticar (no instala nada).

Códigos de salida: `0` aceptado o instalado · `1` rechazado o fallo · `2` uso incorrecto o sin `sudo`.

## Pruebas

```
cd packages/nimbo-update-offline && python3 -m pytest -q     # necesita gpg y gpgv
```

Las pruebas generan **claves de prueba efímeras** en un directorio temporal, que se borra
al terminar; ninguna clave entra al repositorio. Cubren un lote válido (se acepta) y estas
manipulaciones, que deben rechazarse: sin firma, sin manifiesto, manifiesto alterado tras
firmar, firma de otra clave, firma basura, un byte cambiado en un `.deb`, un `.deb` extra
sin firmar, un `.deb` listado que falta, un nombre con ruta (aunque esté firmado), un
manifiesto vacío firmado y (**caso 11**) un lote firmado por otra clave que trae su propio
anillo y pide `--anillo`. Además, un MANIFIESTO que no es UTF-8 o un directorio llamado
`.deb` se rechazan con su motivo, sin *traceback*.

## Pendiente

- **Clave real de actualizaciones:** la genera y custodia Juan José (ADR-015). El paquete
  necesita su **parte pública** en `/usr/share/nimbo/keyrings/nimbo-actualizaciones.gpg`.
- Prueba en una VM bookworm **sin red** (RNF-03, la lleva Juan José): instalar un lote válido
  y comprobar el rechazo de uno manipulado.
- **Límite de v1 — repetición:** un lote viejo pero bien firmado sigue siendo válido. La
  bajada de versión la frena `apt-get -y` (sin `--allow-downgrades` se niega), pero falta
  comprobarlo en la VM. Mejora posible: fecha o número de serie dentro del MANIFIESTO firmado.
