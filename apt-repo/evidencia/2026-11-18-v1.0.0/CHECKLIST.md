# Evidencia que falta recopilar sobre el tag final

Todos los puntos de esta lista son de la futura validación; preparar la VM no
los da por cumplidos.

- [ ] Tag v1.0.0 creado por Juan José y commit completo resuelto.
- [ ] Run/attempt de apt-repo en main, modo v1.0.0, publicado correctamente.
- [ ] Estado limpio de la VM antes de instalar certificado y fuente.
- [ ] Certificado público, huella primaria comprobada y SHA-256.
- [ ] InRelease, Release, Release.gpg y estados GOODSIG + VALIDSIG aceptados.
- [ ] Date y Valid-Until firmados (30 días); publicación aún vigente.
- [ ] PROCEDENCIA.json con hash firmado, candidate=false y commit del tag.
- [ ] Lista de los cinco módulos y versiones exactas del tag.
- [ ] apt-get update: salida y código 0.
- [ ] Descarga desde Pages: versiones, hashes y códigos de salida.
- [ ] Instalación exacta: salida, código 0 y dpkg-query final.
- [ ] Checkout real del tag dentro de esa VM y commit registrado.
- [ ] APT negativo InRelease alterado: rechazo y salida.
- [ ] APT negativo deb alterado: rechazo y salida.
- [ ] APT negativo clave incorrecta: rechazo y salida.
- [ ] Control positivo de transporte y código de salida de la batería.
- [ ] RESULTADOS.md con alcance y fecha real, sin credenciales ni claves privadas.
- [ ] SHA256SUMS de los archivos públicos y verificación de sus sumas.
- [ ] README/Checkpoint actualizados con resultados reales.
- [ ] PR revisado y aceptado por Juan José.

Si cualquier compuerta falla, conservar su salida y describir el fallo; no
completar la lista ni presentar una instalación del candidato como v1.0.0.
