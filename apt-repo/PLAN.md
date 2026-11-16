# RF-DIST-01: checkpoint aprobado

Entrega candidata hasta el 23-nov: cinco módulos de modulos.list, construidos
desde un commit fijo de main con la receta determinista de la ISO. Suite
bookworm, componente main. No se denomina 1.0 al rc1 ni al candidato de main.
La aceptación final exige publicar los paquetes del tag v1.0.0 y repetir la
instalación exacta. No se modifica la ISO ni se activa una fuente APT en ella.

Ajustes aprobados por Juan José:
- Valid-Until de 30 días, renovación expresa aprobada por él. No se desactiva.
- Reutilizar release/firmar.py para la subclave y release/release.py para el
  criterio GOODSIG + VALIDSIG. Rechazar revocación y caducidad, aunque gpgv
  termine en 0. Una prueba real para cada caso.
- Firma en environment release, con su aprobación, sobre los mismos bytes ya
  verificados y con digest fijado entre jobs. No reconstruir al firmar.
- Pages publica el sitio ENTERO en cada despliegue. El sitio está inicialmente
  vacío; cuando haya más contenido deberá integrarse en el mismo artifact.
- Orden: scripts/tests locales, evidencia en VM, workflow al final. Si no llega
  el workflow al 23-nov, Juan José firma manualmente una vez.

Pages está activado con origen GitHub Actions. El environment github-pages
solo acepta main. El primer despliegue requiere el checkpoint del workflow;
no se ejecuta ni despliega desde el PR. URL prevista:
https://teamlocknet.github.io/nimbo/apt/.

La clave real y la aprobación las controla Juan José. Ninguna clave privada
se añade al repositorio ni a artifacts. Las pruebas usan identidades efímeras.
