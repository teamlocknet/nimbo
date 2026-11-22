# Distribución firmada — RF-DIST-01

**Responsables:** Alejandro (pipeline y repositorio APT) y Juan José (custodia y aprobación de firma).

## Qué hace

- **Release firmado en GitHub:** ISO, `SHA256SUMS`, su firma, la procedencia y la clave pública.
- **Repositorio APT firmado** en GitHub Pages con los cinco paquetes de nimbo.
- **La firma exige aprobación humana.** El workflow comprueba que dos compilaciones dan el mismo
  SHA-256 y que esa ISO pasó QEMU; solo entonces Juan José aprueba la firma.
- **La clave maestra está fuera de línea.** CI solo tiene una subclave de firma, con frase propia y
  caducidad.

## Cómo se prueba

| Qué | Prueba |
|---|---|
| Release | Descarga desde las URL públicas, sin iniciar sesión: `sha256sum -c`, firma y huella |
| Canal de la huella | La huella se publica en dos sitios independientes de la clave que viaja con la ISO |
| APT | Firma con la clave de release, procedencia y hash de cada `.deb` |
| APT negativo | `InRelease` alterado, paquete alterado y clave incorrecta deben rechazarse |

## Qué se midió

| Medida | Resultado |
|---|---|
| Release `v1.0.0` (run `44737048128`) | Cinco ficheros verifican desde las URL públicas |
| ISO publicada frente a la instalada en QEMU | **Idéntica byte a byte** |
| APT `v1.0.0` (run `44824465730`, 21-nov) | Firma buena, `candidate: false`, tag `v1.0.0`, commit `94f9b8f` |
| Los cinco `.deb` publicados | Coinciden con el SHA-256 de la procedencia |
| Vigencia del APT | `Valid-Until` 20-dic-2026 |
| Ensayo del candidato (16-nov) | Instalación en VM bookworm limpia; dos compilaciones con los mismos `.deb` |

Huella primaria: `0C50 B739 1A9B 8CFF 8A36  A627 D3B9 111F EC57 48C6`.

## Hallazgos

1. **`gpgv` aceptaba firmas de claves revocadas.** Devuelve código 0 y `VALIDSIG` también con una
   subclave revocada o caducada. Ahora se exige la firma buena y se rechaza cualquier estado de
   revocación o caducidad (#74).
2. **El primer release falló tres veces, y cada fallo dejó su prueba.** Permisos del token para crear
   el tag, una llamada mal hecha y un 403 al crear el borrador (#86, #87 y #88). Nada se publicó a
   medias.

## Lo que falta

**Instalar desde el APT `v1.0.0` en una VM limpia**, con las pruebas negativas. La publicación ya
está verificada desde fuera; RF-DIST-01 se cierra con esa validación (Alejandro).

*Evidencia:* `apt-repo/evidencia/2026-11-16-bookworm/RESULTADOS.md` y
[release `v1.0.0`](https://github.com/teamlocknet/nimbo/releases/tag/v1.0.0) · *Diseño:* ADR-015 ·
*Procedimiento:* `release/README.md` y `apt-repo/README.md`
