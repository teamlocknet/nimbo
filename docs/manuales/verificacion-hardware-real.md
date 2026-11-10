# Verificación en hardware real (semana del 17-nov-2026)

Guion para comprobar **con los ojos**, en una máquina física con UEFI y TPM 2.0, lo que
QEMU no puede probar. Cada punto dice qué mirar y qué cuenta como OK. Lo que se verifique
se anota en la tabla final con fecha, modelo de máquina y evidencia (foto o salida de
comando).

Todo lo de este guion ya pasó en QEMU (Secure Boot con el OVMF de Debian y swtpm). Aquí se
busca lo que solo aparece con firmware, TPM, teclado, pantalla y RAM reales.

## Antes de empezar

- **ISO:** la de `main` después de #54 (firmware explícito, ADR-018). Anotar su SHA-256 y
  el run de CI del que sale. Comprobarla antes de grabarla: `sha256sum -c`.
- **USB de herramientas** (aparte de la de la ISO), con:
  `security/luks-tpm/nimbo-tpm-setup`, `iso/live-build/probar-tpm.sh` e
  `iso/live-build/verificar-instalado.sh`.
- **La instalación es de prueba**, en un disco que se puede borrar. Contraseñas propias de
  la prueba, que solo teclea quien está delante de la máquina.
- **Credenciales (regla del proyecto):** la fase 2 de `nimbo-tpm-setup` muestra una
  **clave de recuperación**. **No se fotografía** esa pantalla ni se copia a ningún fichero
  del repo. Si una evidencia la contiene, se redacta antes de guardarla. Nadie dicta
  contraseñas a nadie.

## Máquina

| Campo | Valor |
|---|---|
| Fabricante / modelo | |
| Firmware (versión UEFI) | |
| TPM | (fTPM / dTPM, versión) |
| CPU / RAM total | |
| GPU | |
| Red por cable (chip) | (`lspci -nn \| grep -i ether`) |
| Teclado físico | (distribución) |

## 1. Arranque de la ISO live

- [ ] Arranca en **UEFI con Secure Boot activo** (sin desactivarlo en el firmware).
      OK = llega al escritorio Xfce. En una terminal: `mokutil --sb-state` → `SecureBoot enabled`.
- [ ] Arranca en **BIOS legacy / CSM**, si la máquina lo ofrece. *(Nunca verificado:
      ADR-006 lo deja como opcional.)*
- [ ] Ojo: el **escritorio live está en inglés**. El lanzador se llama
      **"Install nimbo (encrypted, …)"**; Calamares sí sale en español.

## 2. Instalación cifrada (lanzador "Install nimbo (encrypted, …)")

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
      que la contraseña desbloquea a la primera. *Contexto:* cryptsetup calibra argon2id en la
      máquina donde se instala (QEMU, 8-nov: 1 GiB → ~438 MiB, 1536 MiB → ~307 MiB, 4 GiB →
      1 GiB) y el mínimo declarado es **1 GiB instalando en la propia máquina** (ADR-009).
      Anotar los parámetros del keyslot: `sudo cryptsetup luksDump /dev/<raíz> | grep -E
      'PBKDF|Memory|Time'`. Si el disco se instaló en otra máquina con más RAM y aquí falla,
      el aviso de H-002 tiene que explicar que es la memoria, no la contraseña.
- [ ] Arranca hasta el greeter **sin** autologin (D14).
- [ ] Dentro del instalado, con la USB de herramientas montada:
      `sudo sh <usb>/verificar-instalado.sh --secure-boot` → `VEREDICTO: OK — 0 fallos`
      (en QEMU, 10-nov: 0 fallos, RAM 378 MiB).

## 3. Hermetismo, RAM y firmware en la máquina real

Con el **cable de red conectado** (es la prueba que importa: hay red disponible y el
sistema no debe usarla).

- [ ] **Sin red levantada:** `ip -br addr` → la interfaz cableada sin dirección IPv4 (solo,
      como mucho, una IPv6 `fe80::`). *Contexto:* el sistema no configura ninguna interfaz;
      en QEMU no pidió ni DHCP (10-nov). La red a demanda (`nimbo-red`) es posterior
      (ADR-012).
- [ ] **Sin puertos escuchando:** `ss -tulpn` → tabla vacía.
- [ ] **RAM en reposo:** sesión iniciada, 90 s sin tocar nada, `free -m` → "usado" < 500 MB.
- [ ] **Firmware que falta (ADR-018):** `sudo dmesg | grep -iE 'firmware|direct firmware load'`.
      Anotar cada línea. La ISO solo lleva firmware de `main`: el de `non-free-firmware`
      (red Realtek `rtl_nic`, Wi-Fi Intel `iwlwifi`, GPU AMD `amdgpu`) **no está**. OK = la
      pantalla, el teclado, el disco y la red por cable funcionan igual. Si algo de eso
      falla por firmware, **es un hallazgo de entregable**: anotar el chip y el fichero que
      pide.
- [ ] **Wi-Fi:** fuera de v1 (no hay `wpasupplicant`). Solo se anota si la tarjeta aparece
      (`ip -br link`).

## 4. TPM 2.0 (`nimbo-tpm-setup`, ADR-008)

Validado en QEMU + swtpm: V2–V8 (`security/luks-tpm/evidencia/2026-11-04-V3-V8.md`) y
hermetismo tras el TPM (`…/2026-11-10-hermetismo-post-tpm.md`). Los comandos usan la USB de
herramientas; `nimbo-tpm-setup` todavía no va dentro de la ISO.

- [ ] **TPM presente:** `cat /sys/class/tpm/tpm0/tpm_version_major` → `2`.
- [ ] **Fase 1 (dracut):** `sudo sh <usb>/nimbo-tpm-setup`. OK = termina sin rollback.
      Reiniciar: pide la contraseña como siempre y la contraseña con símbolos entra **a la
      primera** con el teclado físico (*QEMU 10/10, `…/2026-10-23-teclado-dracut.md`*).
- [ ] **Fase 2 (sellado PCR 7+9):** `sudo sh <usb>/nimbo-tpm-setup` otra vez. Pide confirmar
      la clave de recuperación **entera**: apuntarla en papel, **sin foto**. OK = `FASE 2
      COMPLETA`.
- [ ] **Desbloqueo automático, 3 arranques seguidos sin teclear (V4).** OK = llega al
      greeter sin pedir contraseña las tres veces. Anotar el tiempo hasta el greeter.
      *Riesgo que solo se ve aquí:* si el firmware o GRUB cambian lo que mide el PCR 9 en
      cada arranque (p. ej. `grubenv`), el TPM no abrirá nunca. En QEMU no pasó en 9
      arranques.
- [ ] **Manipulación de `/boot` (V5):** `sudo sh <usb>/probar-tpm.sh --manipular-initrd` y
      reiniciar. OK = **pide la contraseña** (el TPM se niega) y la contraseña abre. Luego
      `sudo sh <usb>/probar-tpm.sh --restaurar-initrd`, reiniciar: vuelve a abrir solo (V6a).
      *(`probar-tpm.sh` además escribe en la consola serie; en hardware real eso se pierde y
      da igual: lo que cuenta es lo que se ve en pantalla.)*
- [ ] **Actualización legítima + resellado (V6b/V7):** `sudo sh <usb>/probar-tpm.sh
      --regenerar-initrd`, reiniciar → pide contraseña. Dentro:
      `sudo sh <usb>/nimbo-tpm-setup --reseal` → `RESELLADO COMPLETO`; reiniciar → abre solo.
- [ ] **Clave de recuperación:** en un arranque que pida contraseña (p. ej. tras V5),
      teclear la clave de recuperación en vez de la contraseña. OK = abre.
- [ ] **Evidencia sin credenciales:** `sudo sh <usb>/nimbo-tpm-setup --estado` y
      `sudo cryptsetup luksDump /dev/<raíz> | grep -E 'Keyslots|Tokens|tpm2'` (no muestran la
      clave de recuperación). Se pueden fotografiar o copiar.
- [ ] **Hermetismo tras el TPM:** repetir `ss -tulpn` (vacía) e `ip -br addr` del punto 3.
- [ ] *Riesgo a anotar:* una actualización del firmware UEFI o de las llaves de Secure Boot
      cambia el PCR 7 → el arranque pedirá la contraseña y hará falta `--reseal`. No se
      provoca; se deja escrito para el manual.

## Resultado

| Punto | Resultado | Evidencia | Fecha |
|---|---|---|---|
| | | | |
