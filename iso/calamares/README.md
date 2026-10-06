# iso/calamares

Instalador de nimbo (Calamares). Decisiones en
[ADR-006](../../docs/adr/ADR-006-cadena-de-arranque-instalador.md).

**Dueño:** Juan José

## Dónde vive la receta

live-build consume el overlay desde `iso/live-build/config/`, así que la configuración
del instalador está allí y no en esta carpeta:

| Qué | Ruta (bajo `iso/live-build/`) |
|---|---|
| Paquetes del instalador | `config/package-lists/installer.list.chroot` |
| Excepción de backports (solo `calamares`) | `config/archives/nimbo-backports.pref.chroot` + `auto/config` |
| Configuración de Calamares | `config/includes.chroot/etc/calamares/` |
| Scripts que corren en el disco destino | `config/includes.chroot/usr/lib/nimbo/calamares/` |
| Lanzador de la sesión live | `config/includes.chroot/usr/bin/nimbo-instalar`, `…/lib/live/config/0160-nimbo-instalador` |
| Pool APT local + auditoría de backports | `config/hooks/normal/0200-…` y `0210-…` |
| Arnés de instalación en QEMU | `install-in-qemu.sh`, `verificar-instalado.sh` |

## Guía de instalación (3C.1)

1. Arranca la ISO en modo **UEFI**. En el escritorio live, abre **Instalar nimbo**
   (icono del escritorio o menú *Aplicaciones → Sistema*). Si Xfce avisa de que el
   lanzador no es de confianza, elige *Lanzar de todos modos*.
2. **Teclado:** elige la distribución.
3. **Particiones:** solo hay instalación guiada (*Borrar disco*). **Borra el disco
   entero.** El resultado es: ESP + `/boot` ext4 **sin cifrar** + raíz ext4 sobre **LUKS2**.
4. **Cifrado:** la casilla *Cifrar sistema* viene **marcada**. Déjala así y escribe una
   contraseña que recuerdes: **es la única forma de abrir el disco** y se pedirá en cada
   arranque.
   > ⚠️ El instalador **no mide la fortaleza** de la contraseña de cifrado ni avisa si es
   > corta: acepta incluso un carácter. Es la que protege todo el disco: usa una frase
   > larga.
   > ⚠️ El cifrado es **opcional**: si desmarcas la casilla, el sistema se instala **sin
   > LUKS** y `nimbo-tpm-setup` no podrá vincular nada al TPM después.
5. **Usuario:** nombre y contraseña. La casilla *exigir contraseñas fuertes* viene
   marcada (mínimo 8 caracteres); puedes desmarcarla si quieres otra contraseña. La
   casilla de inicio de sesión automático viene desmarcada y, aunque se marque, **no
   tiene efecto**: el sistema instalado nunca entra solo (D14).
6. Al terminar, reinicia y retira la ISO. El arranque pide la contraseña LUKS y llega a
   la pantalla de inicio de sesión.

## Qué NO hace todavía (3C.2 o posterior)

- Particionado manual, swap, idioma y zona horaria del sistema instalado (queda en
  `C.UTF-8` / UTC). El instalador sí abre en español.
- TPM 2.0: lo añadirá `nimbo-tpm-setup` (D17), que cambiará el initramfs a `dracut`.
- **Secure Boot activo: NO VERIFICADO.** Arranque en BIOS legacy: NO VERIFICADO.
