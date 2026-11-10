// nimbo-nav — preferencias por defecto de firefox-esr (ADR-012, RF-NAV-01).
// Se instala en /usr/lib/firefox-esr/defaults/pref/: Firefox lo lee siempre al arrancar.
// Cubre lo que la política "Preferences" de policies.json no admite (prefijos
// toolkit.*, datareporting.*, app.normandy.*, services.*, extensions.*, media.gmp-*).
// Cada ajuste se confirma con el pcap en reposo (pruebas/prueba-reposo-navegador.sh).

// Telemetría y reportes
pref("toolkit.telemetry.enabled", false);
pref("toolkit.telemetry.unified", false);
pref("toolkit.telemetry.archive.enabled", false);
pref("toolkit.telemetry.server", "");
pref("toolkit.telemetry.updatePing.enabled", false);
pref("toolkit.telemetry.bhrPing.enabled", false);
pref("toolkit.telemetry.firstShutdownPing.enabled", false);
pref("toolkit.telemetry.newProfilePing.enabled", false);
pref("toolkit.telemetry.shutdownPingSender.enabled", false);
pref("toolkit.coverage.endpoint.base", "");
pref("datareporting.healthreport.uploadEnabled", false);
pref("datareporting.policy.dataSubmissionEnabled", false);
pref("browser.crashReports.unsubmittedCheck.autoSubmit2", false);
pref("breakpad.reportURL", "");

// Estudios y experimentos remotos
pref("app.normandy.enabled", false);
pref("app.normandy.api_url", "");
pref("app.shield.optoutstudies.enabled", false);

// Extensiones: sin actualizaciones ni recomendaciones automáticas
pref("extensions.update.enabled", false);
pref("extensions.update.autoUpdateDefault", false);
pref("extensions.getAddons.cache.enabled", false);
pref("extensions.systemAddon.update.enabled", false);
pref("extensions.systemAddon.update.url", "");
pref("extensions.htmlaboutaddons.recommendations.enabled", false);

// Complementos multimedia (descarga de OpenH264/Widevine al arrancar)
pref("media.gmp-manager.updateEnabled", false);
pref("media.gmp-manager.url", "");
pref("media.gmp-gmpopenh264.enabled", false);
pref("media.gmp-widevinecdm.enabled", false);

// DNS sobre HTTPS apagado (modo 5 = desactivado a propósito)
pref("network.trr.mode", 5);

// Remote Settings: EXPERIMENTAL. Sin servidor no hay sincronización al arrancar.
// Pendiente de medir que el navegador siga funcionando (ADR-012, "pendiente de medir").
pref("services.settings.server", "data:,");
pref("services.settings.poll_interval", 0);
