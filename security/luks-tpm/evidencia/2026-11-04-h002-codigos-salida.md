# H-002 — códigos de salida reales de cryptsetup en los dos fallos por memoria (2026-11-04)

**Estado:** medido. Cierra la pregunta "¿qué código devuelve cryptsetup en cada modo de
fallo?" que quedaba pendiente para elegir el mensaje honesto de H-002. **No decide** la
opción de mensaje (1 o 2): eso lo decide Juan José.

## Qué se midió

En un contenedor `debian@sha256:88200866…4171` (la misma imagen anclada del build), con
`cryptsetup-bin 2:2.6.1-4~deb12u2`, **la misma versión que lleva la ISO**
(`chroot.packages.install`). Los paquetes se instalaron desde `deb.debian.org`, porque
snapshot.debian.org no respondía desde el contenedor ese día. La versión coincide con la
del snapshot anclado.

Un archivo de 32 MiB formateado como LUKS2 con los **mismos parámetros que eligió
Calamares** en el disco instalado: `argon2id`, memoria 1 048 576 KiB, coste 6, 2 hilos
(`--pbkdf-force-iterations 6` para no depender de la calibración). La clave se generó al
vuelo (`/dev/urandom`) y se destruyó con `shred` al terminar. No se usó ninguna
contraseña real y no hay ninguna credencial en esta evidencia.

Se usó `cryptsetup open --test-passphrase`, que deriva la clave de argon2id igual que el
desbloqueo real, pero no necesita device-mapper.

## Resultado

| Caso | Cómo se provoca | Mensaje de cryptsetup | Código |
|---|---|---|---|
| A. Clave correcta | sin límite | — | **0** |
| B. Clave incorrecta | otra clave | `No key available with this passphrase.` | **2** |
| C. Sin memoria para argon2id | `ulimit -v 700000` (la reserva de memoria falla) | `Not enough available memory to open a keyslot.` | **3** |
| D. OOM-kill | cgroup de 600 MiB (`docker run -m 600m --memory-swap 600m`) | `Killed` | **137** (128 + SIGKILL) |

Coincide con el man de bookworm (2 = contraseña, 3 = memoria) y con lo visto en QEMU:
el mensaje del caso C es el mismo que salió con 1024, 768 y 512 MiB, y el caso D es el
`Out of memory: Killed process (cryptsetup)` de 1280 MiB.

**Límite:** en C la falta de memoria se simuló limitando el espacio de direcciones del
proceso. En la VM pudo salir por otro camino interno de libcryptsetup. El mensaje y el
código son los mismos en los dos casos, porque ambos terminan en `-ENOMEM` → 3.

## Dónde se pierde el código (initramfs-tools de bookworm)

`cryptsetup-initramfs 2:2.6.1-4~deb12u2`, `scripts/local-top/cryptroot`:

```sh
run_keyscript "$count" | unlock_mapping      # interactivo
rv=$?
...
if [ $rv -ne 0 ]; then
    cryptsetup_message "ERROR: $CRYPTTAB_NAME: cryptsetup failed, bad password or options?"
```

`unlock_mapping` (`/lib/cryptsetup/functions`) termina con la llamada a `/sbin/cryptsetup
-T1 … open`. Por eso **`rv` sí contiene el código real** (2, 3 o 137): no lo pierde la
tubería, lo descarta el mensaje, que trata igual cualquier valor distinto de 0.

## Qué implica para las dos opciones de mensaje (para decidir)

- **Opción 1** (aviso antes del prompt, comparando el coste del keyslot con `MemAvailable`):
  no depende de estos códigos. Funciona igual.
- **Opción 2** (mensaje según el código real): **es viable**. El código llega intacto a
  `rv`, así que bastaría distinguir 2 / 3 / 137. Habría que hacerlo con un envoltorio de
  `/sbin/cryptsetup` en el initramfs o con un parche de `cryptroot`. Cualquiera de los dos
  toca el initramfs del producto, así que es **checkpoint de receta**.

## Cómo reproducirlo

El script usado está en el anexo. Se corre así, en tres pasadas (formatear, normal y oom),
con un volumen temporal en `/datos`:

```sh
IMG=docker.io/library/debian@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171
docker run --rm -v "$PWD/prueba.sh:/prueba.sh:ro" -v "$PWD/datos:/datos" $IMG /prueba.sh formatear
docker run --rm -v "$PWD/prueba.sh:/prueba.sh:ro" -v "$PWD/datos:/datos" $IMG /prueba.sh normal
docker run --rm -m 600m --memory-swap 600m -v "$PWD/prueba.sh:/prueba.sh:ro" -v "$PWD/datos:/datos" $IMG /prueba.sh oom
# después: destruir datos/k y datos/disco.img
```

### Anexo — `prueba.sh`

```sh
#!/bin/sh
set -u
MODO="$1"; D=/datos
apt-get -qq update >/dev/null && apt-get -qq install -y cryptsetup-bin >/dev/null 2>&1
echo "cryptsetup: $(cryptsetup --version) · paquete $(dpkg-query -W -f '${Version}' cryptsetup-bin)"
case "$MODO" in
formatear)
  head -c 48 /dev/urandom | base64 | tr -d '\n' > $D/k   # clave de prueba efímera
  truncate -s 32M $D/disco.img
  cryptsetup luksFormat --batch-mode --type luks2 --pbkdf argon2id --pbkdf-memory 1048576 \
     --pbkdf-parallel 2 --pbkdf-force-iterations 6 --key-file $D/k $D/disco.img
  cryptsetup luksDump $D/disco.img | grep -E 'PBKDF|Memory|Time cost|Threads' ;;
normal)
  cryptsetup open --test-passphrase --key-file $D/k $D/disco.img; echo "A rc=$?"
  echo -n incorrecta > /tmp/mala
  cryptsetup open --test-passphrase --key-file /tmp/mala $D/disco.img; echo "B rc=$?"
  ( ulimit -v 700000; cryptsetup open --test-passphrase --key-file $D/k $D/disco.img; echo "C rc=$?" ) ;;
oom)
  cryptsetup open --test-passphrase --key-file $D/k $D/disco.img; echo "D rc=$?" ;;
esac
```
