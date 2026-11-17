# Manual — Red privada del equipo (`nimbo-net`, WireGuard)

**Para:** dos integrantes de un equipo que quieren unir sus equipos nimbo con un túnel
cifrado. **Requisitos:** RF-RED-01, RNF-06. **Diseño:**
[ADR-011](../adr/ADR-011-red-privada-wireguard.md). **Detalle técnico y límites:**
[`packages/nimbo-net`](../../packages/nimbo-net/README.md) (de Alejandro).

`nimbo-net` crea un túnel **WireGuard** directo entre **dos** equipos (interfaz `wg-nimbo`).
No arranca solo, no abre servicios y no cambia la salida a internet: solo une los dos equipos.

## 1. Preparación (una vez por equipo, 15 min)

Cada equipo genera **su propia** clave; la privada **nunca sale del equipo** (ni por USB, ni por
chat, ni al repositorio):

```
sudo install -d -m 0700 /etc/nimbo-net
sudo sh -c 'set -euC; umask 077; wg genkey > /etc/nimbo-net/private.key; wg pubkey < /etc/nimbo-net/private.key > /etc/nimbo-net/public.key'
cat /etc/nimbo-net/public.key        # esta (la pública) sí se comparte
```

Intercambiad **solo las claves públicas**, comprobando de quién viene cada una. Después, cada
uno crea `/etc/nimbo-net/perfil.json` (dueño root, permisos 0600):

```json
{
  "version": 1,
  "address": "10.90.0.1",
  "peer_address": "10.90.0.2",
  "peer_public_key": "CLAVE_PUBLICA_DEL_OTRO_EQUIPO",
  "endpoint": "IP_DEL_OTRO_EQUIPO",
  "endpoint_port": 51820,
  "listen_port": 51820,
  "timeout": 120
}
```

En el **otro** equipo se invierten `address` y `peer_address`, y se ponen la clave pública y
la IP del primero. Usa direcciones privadas que no choquen con tu red.

## 2. Unirse (los dos equipos, a la vez)

```
sudo nimbo-red on          # red por cable (ver red-por-cable.md)
sudo nimbo-net join        # en los DOS equipos, dentro de unos 2 minutos
nimbo-net status
```

`join` espera al otro equipo y solo dice "conectado" cuando hay *handshake* y el otro
responde al ping. Si el otro bloquea el ping, no se declara conectado.

## 3. Salir

```
sudo nimbo-net leave       # quita el túnel y sus rutas
sudo nimbo-red off         # apaga la red
```

Tras reiniciar, el túnel **no** vuelve solo. `nimbo-net status` sin túnel → `nimbo-net:
inactivo` (medido en la ISO, 16-nov).

## Bueno saber

- **El modo Tor y la red del equipo no pueden estar activos a la vez** en esta versión:
  `join` se niega con el modo Tor encendido y `nimbo-tor on` se niega con el túnel puesto.
- Un apagado brusco puede dejar el túnel a medias: `sudo nimbo-net leave` lo limpia.
- Sin relay ni Wi-Fi: los dos equipos tienen que alcanzarse directamente por IP.

## Cómo se verificó

RF-RED-01 sobre la ISO integrada, **dos instalaciones** cifradas en QEMU, 64 comprobaciones
correctas (Alejandro, #84):
[`RESULTADOS-INTEGRADA.md`](../../packages/nimbo-net/pruebas/laboratorio/RESULTADOS-INTEGRADA.md).
