# Actualización sin conexión (`nimbo-update-offline`) — RF-UPD-01

**Autor:** Emmanuel. **Aceptación** (prueba sin red e integración): Juan José, dentro de RNF-03.

## Qué hace

Instala actualizaciones traídas en una USB **solo si vienen firmadas** con la clave de nimbo.
Un lote es: los `.deb`, un `MANIFIESTO` con el SHA-256 de cada uno y la firma GPG del manifiesto.

- **Se rechaza ante cualquier duda:** sin firma, firma de otra clave, un byte cambiado, un
  paquete de más o de menos, nombres con rutas, manifiesto vacío.
- **Verifica la copia, no la USB:** copia el lote a un directorio propio y comprueba esa copia,
  para que nadie cambie un paquete entre la verificación y la instalación.
- **Sin red:** instala con `apt-get` sin ninguna fuente remota, así que no puede descargar nada.
- **No acepta otra clave al instalar:** `instalar` no tiene opción `--anillo`, así que un lote
  no puede traer su propia clave y pedir que se use.

## Cómo se prueba

Firmas **reales** con GPG y claves de prueba **efímeras** (se crean y se borran en cada
ejecución; ninguna clave entra al repositorio).

## Qué se midió

| | Resultado |
|---|---|
| Lote con firma válida | **se acepta** |
| 10 lotes manipulados (sin firma, sin manifiesto, manifiesto alterado, otra clave, firma basura, byte cambiado, `.deb` extra, `.deb` ausente, ruta firmada, manifiesto vacío) | **10/10 rechazados**, cada uno con su motivo (100 %) |
| Caso 11: lote de otra clave que trae su anillo y pide `--anillo` | rechazado: la opción no existe en `instalar` |
| Datos raros (manifiesto no UTF-8, directorio llamado `.deb`) | rechazados con motivo, sin errores internos |
| Pruebas | rojo → verde: **20 passed**, en CI con el Python de bookworm |

## Hallazgos

1. **`--anillo` en `instalar` era una puerta trasera** (lo vio Juan José): con esa opción se
   aceptaba un lote firmado por cualquiera. Se quitó y se añadió como caso 11.
2. **`instalar` no habría instalado nada en la realidad** (#70): con `.deb` locales,
   `apt-get --no-download` falla en bookworm (`Internal Error, Pathname to install is not
   absolute`). Las pruebas unitarias simulan `apt-get` y no podían verlo; salió al medir en la
   VM la bajada de versión. Ahora `apt` corre sin fuentes remotas.
3. **Las pruebas exigen el motivo del rechazo, no solo el rechazo:** un fallo de rutas en Windows
   hizo fallar el caso válido, y así se comprobó que los rechazos no pasan "por accidente".

## Límites declarados

Un lote **viejo** pero bien firmado sigue siendo válido. Lo que sí está medido (VM, 11-nov,
`pruebas/prueba-bajada-version.sh`, #70): `apt` **se niega a bajar de versión** (la 1.0 se
rechaza con código 100 y la 2.0 sigue instalada). Repetirlo con un lote firmado y sin red queda
para la prueba de Juan José (RNF-03).
La clave real la genera y custodia Juan José (ADR-015).

*Diseño:* ADR-013 · *Procedimiento por USB:* `packages/nimbo-update-offline/README.md`
