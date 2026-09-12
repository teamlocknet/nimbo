# iso/xfce4

Personalización y hardening del entorno de escritorio **Xfce4** para la ISO (Core OS).

**Dueño:** Juan José

---

## Estado: Paso 3A — escritorio mínimo (hecho) · 3B — personalización (pendiente)

El escritorio Xfce4 **entra en la ISO por una lista de paquetes curada**, no por opciones
de `lb config`. La lista vive versionada en:

    iso/live-build/config/package-lists/desktop.list.chroot

**Por qué una lista y no un metapaquete:** el metapaquete `xfce4` (o `task-xfce-desktop`)
arrastra *goodies*, ofimática y multimedia que disparan la RAM y meten no-determinismo. Con
`--apt-recommends false` (ya en `auto/config`) los paquetes "Recomienda" no se cuelan, así
que declaramos **explícito y quirúrgico** solo lo imprescindible para una sesión de trabajo
de auditoría.

### Qué se incluye (y por qué cada pieza)

| Grupo | Paquetes | Razón |
|---|---|---|
| Núcleo Xfce | `xfce4-session xfwm4 xfce4-panel xfce4-settings xfdesktop4 thunar xfce4-terminal` | Sesión de escritorio imprescindible. |
| Bus de sesión | `dbus-x11` | Xfce necesita `dbus-launch`. |
| Servidor X | `xserver-xorg-core xserver-xorg-input-libinput xserver-xorg-video-fbdev xserver-xorg-video-vesa` | Con `recommends=false` los metapaquetes `xserver-xorg`/`*-video-all` **no** traen drivers (son "Recomienda"). `modesetting` (en `-core`, vía KMS) cubre la std-VGA de QEMU y el HW moderno; `fbdev`+`vesa` son el colchón para gama baja real. |
| Login manager | `lightdm lightdm-gtk-greeter` | El DM más ligero con autologin gestionado por `live-config`; arranca la sesión gráfica sola. El greeter es "Recomienda" → explícito. |
| Fuente base | `fonts-dejavu-core` | X necesita ≥1 fuente; mínima y determinista. |

### Qué se excluye deliberadamente

Metapaquetes `xfce4` / `task-xfce-desktop`, `xfce4-goodies`, plugins extra, gestor de red
GUI, **navegador** (llega por la Vía B / paso de navegación), salvapantallas y temas extra.
Con `recommends` global OFF las dependencias blandas ya no se cuelan; aun así evitamos los
metapaquetes por RAM y determinismo.

### Techo de RAM idle

Objetivo del Acta/RNF-04: **< 500 MB de RAM usada** con el escritorio arrancado y en reposo.
La medición es **host-side y honesta** (no se hornea nada de medición en la imagen): ver
`iso/live-build/measure-ram-in-qemu.sh` y el número obtenido en `iso/live-build/README.md`.

---

## Lo que NO está en este paso (anti-desborde)

La **personalización real** del escritorio (temas, paneles, ajustes por defecto, wallpaper)
y el **hardening** (políticas, sysctl, telemetría off) son el **Paso 3B** y el trabajo de
`security/hardening/`. Aquí solo se consigue que la ISO **arranque a un escritorio Xfce4
funcional** por debajo del techo de RAM.
