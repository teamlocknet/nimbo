# Verificación en hardware real (semana del 17-nov-2026)

Guion para comprobar **con los ojos**, en una máquina física con UEFI y TPM 2.0, lo que
QEMU no puede probar. Cada punto dice qué mirar y qué cuenta como OK. Lo que se verifique
se anota con fecha, modelo de máquina y evidencia (foto o salida de comando).

> Esqueleto inicial (2026-10-23). Se completa con los pasos de `nimbo-tpm-setup` cuando
> exista (Paso 4).

## Máquina

| Campo | Valor |
|---|---|
| Fabricante / modelo | |
| Firmware (versión UEFI) | |
| TPM | (fTPM / dTPM, versión) |
| GPU | |
| Teclado físico | (distribución) |

## 1. Arranque de la ISO live

- [ ] Arranca en **UEFI con Secure Boot activo** (sin desactivarlo en el firmware).
      OK = llega al escritorio Xfce. En una terminal: `mokutil --sb-state` → `SecureBoot enabled`.
- [ ] Arranca en **BIOS legacy / CSM**, si la máquina lo ofrece. *(Nunca verificado:
      ADR-006 lo deja como opcional.)*

## 2. Instalación cifrada (lanzador "cifrado, recomendado")

- [ ] La instalación termina sin errores.
- [ ] **El prompt de la contraseña LUKS se ve bien en pantalla.** OK = la línea
      `Please unlock disk luks-…:` legible, sin texto aplastado ni basura en los bordes.
      *Contexto:* en QEMU con el OVMF de Debian 2022.11 y la VGA `std` el prompt sale
      ilegible; se demostró que es del arnés (firmware y tarjeta emulados), no del
      producto: con el mismo disco, otra tarjeta emulada u otro OVMF lo muestran limpio.
      Este punto confirma que en una pantalla real se ve bien. Si se viera roto aquí,
      **es un problema de entregable**: anotar GPU y firmware y no darlo por bueno.
- [ ] La contraseña se teclea con la **distribución elegida** (probar una con símbolos
      que cambien de sitio entre US y ES, p. ej. `ñ`, `-`, `/`).
- [ ] **Desbloqueo con la RAM real de la máquina (H-002).** Anotar la RAM total y comprobar
      que la contraseña desbloquea a la primera. *Contexto:* con los parámetros que elige
      Calamares (argon2id con 1 GiB de memoria cuando instala en una máquina de 4 GiB), el
      desbloqueo falla por debajo de ~1,5 GiB con el mensaje engañoso `cryptsetup failed,
      bad password or options?`. Si la máquina tiene poca RAM, instalar EN ELLA y anotar los
      parámetros del keyslot: `sudo cryptsetup luksDump /dev/<raíz> | grep -E 'PBKDF|Memory|Time'`.
- [ ] Arranca hasta el greeter **sin** autologin (D14).
- [ ] Dentro del instalado: `sudo sh verificar-instalado.sh --secure-boot` → `VEREDICTO: OK`
      (copiar el script desde un USB).

## 3. TPM 2.0 (`nimbo-tpm-setup`, Paso 4)

- [ ] Tras la fase 1 (dracut), la contraseña con símbolos entra **a la primera** con el
      teclado físico. *Medido en QEMU 10/10 (riesgo descartado,
      `security/luks-tpm/evidencia/2026-10-23-teclado-dracut.md`); aquí se confirma con un
      teclado real.*

*(Pendiente: se rellena con el guion de validación del Paso 4 — sellado PCR 7+9 en dos
fases, desbloqueo automático, alterar el initrd y comprobar que cae a la contraseña,
`--reseal`, clave de recuperación.)*

## Resultado

| Punto | Resultado | Evidencia | Fecha |
|---|---|---|---|
| | | | |
