# Guía de instalación y uso de nimbo (Design Partner)

**Para:** la persona externa que valida nimbo (RNF-06 / HT-06). **Tiempo previsto:** una jornada.
Sigue los pasos en orden **sin pedir ayuda**. Si algo no funciona o no se entiende, anótalo
en el [formulario de hallazgos](formulario-hallazgos-design-partner.md) y sigue con el
siguiente paso. Cada tropiezo que anotes nos sirve.

## Antes de empezar (15 min)

- Un equipo x86-64 con firmware **UEFI** y al menos **1 GiB de RAM** (2 GiB recomendado),
  o una máquina virtual con UEFI. **Se borrará el disco de ese equipo.**
- Una memoria USB de 2 GB o más.
- La imagen `nimbo-*.iso` y su `SHA256SUMS`, que te entregará el equipo.

**Comprueba la imagen** antes de usarla. En Linux: `sha256sum -c SHA256SUMS`. En Windows
(PowerShell): `Get-FileHash .\nimbo-*.iso -Algorithm SHA256`, y compara el resultado con el
de `SHA256SUMS`. Si no coinciden, **no sigas**: anótalo como hallazgo.

Graba la ISO en la USB (por ejemplo con Balena Etcher o con `dd`) y arranca el equipo
desde la USB.

## 1. Probar sin instalar: modo live (15 min)

1. Arranca desde la USB. Debes llegar a un escritorio Xfce **sin escribir contraseña**: es
   el modo de prueba, nada se guarda en el disco.
2. Abre una terminal (menú → Terminal) y escribe `nimbo-audit --help`. Debe mostrar la ayuda.

## 2. Instalar (30–45 min)

1. En el escritorio, abre el icono de instalación cifrada. El escritorio live está en inglés,
   así que se llama **"Install nimbo (encrypted, recommended)"** (en español: "Instalar nimbo
   (cifrado, recomendado)"). **No** uses "Install nimbo without encryption (advanced)".
   El instalador (Calamares) sí sale en español.
2. Elige idioma y zona horaria (por defecto: español de Colombia y Bogotá).
3. Crea tu usuario y tu contraseña. El instalador **sugiere** contraseñas fuertes pero no las
   obliga. Elige la **contraseña del disco** y guárdala bien: **sin ella no se recupera nada**.
4. Al terminar, reinicia y retira la USB.
5. Al arrancar, el sistema **pide la contraseña del disco** y luego tu usuario y contraseña.
   No debe entrar solo.

## 3. Registrar una auditoría con evidencia (45 min)

En una terminal del sistema instalado:

```
nimbo-audit init cliente-prueba            # crea el caso en ~/audits/cliente-prueba/
cd ~/audits/cliente-prueba
echo "captura de prueba" > ~/evidencia1.txt
nimbo-audit capture ~/evidencia1.txt       # registra la evidencia con su SHA-256
nimbo-audit report                         # informe en reportes/: cada evidencia OK
nimbo-audit verify                         # comprobación independiente: debe salir OK
```

Ahora **altera una evidencia a propósito**: abre con un editor la copia guardada dentro del
caso (`~/audits/cliente-prueba/evidencia/`), cambia una letra y guarda. Ejecuta otra vez
`nimbo-audit verify`: **debe marcarla como MODIFICADO** y terminar con error.

## 4. Navegar de forma segura (30 min)

> Este paso aplica cuando la ISO ya incluya la navegación segura. Si no tienes Firefox en
> el menú, anótalo y salta al paso 5.

nimbo arranca **sin red**. Para este paso necesitas el equipo conectado **por cable** (o la
máquina virtual con red). El Wi-Fi no está soportado en esta versión.

1. Levanta la red en una terminal: `sudo nimbo-red on`. Debe decir qué interfaz levantó.
2. Abre **Firefox** desde el menú: es el navegador normal, endurecido y sin telemetría.
3. Activa el modo Tor: `nimbo-tor on`. El sistema te pide tu contraseña.
4. Abre **"Navegar por Tor"** desde el menú y visita `https://check.torproject.org`. La página
   debe decir que estás usando Tor. Este modo evita fugas de red, pero no protege frente a la
   huella del navegador.
5. Ejecuta `sudo nimbo-leakcheck`. Debe decir **"OK — 0 fugas"**.
6. Apaga el modo Tor (`nimbo-tor off`) y después la red (`sudo nimbo-red off`).

## 5. Comprobar el endurecimiento (10 min)

> Aplica cuando la ISO incluya el endurecimiento 3B.2.

`sudo /usr/lib/nimbo/verify-hardening`. Debe terminar con **"VEREDICTO: OK — 0 fallos"**.

Si te equivocas 5 veces seguidas con la contraseña, la cuenta se bloquea 10 minutos y el
sistema **te dice que está bloqueada**. No la olvidaste: espera o pide a quien tenga `sudo`
que ejecute `sudo faillock --user <tu-usuario> --reset`.

## Al terminar

Completa el formulario de hallazgos. Indica a qué hora empezaste y a qué hora terminaste,
y en qué pasos necesitaste algo que esta guía no decía.
