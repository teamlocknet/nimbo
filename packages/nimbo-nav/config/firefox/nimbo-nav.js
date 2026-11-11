// nimbo-nav — preferencias por defecto de firefox-esr (ADR-012, RF-NAV-01).
// Se instala en /etc/firefox-esr/: es el mecanismo de Debian para las preferencias del
// sistema (firefox-esr NO aplicaba este fichero en /usr/lib/firefox-esr/defaults/pref/;
// medido en una VM Debian 12 el 10-nov).
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

// Nueva pestaña en blanco, sin precarga ni fondos. Firefox precarga about:newtab aunque
// arranque en about:blank, y esa página descargaba sus fondos (newtab-wallpapers-v2) desde
// firefox-settings-attachments.cdn.mozilla.net: era la última conexión en reposo (VM, 10-nov).
pref("browser.newtabpage.enabled", false);
pref("browser.newtab.preload", false);
pref("browser.newtabpage.activity-stream.newtabWallpapers.enabled", false);

// DNS sobre HTTPS apagado (modo 5 = desactivado a propósito)
pref("network.trr.mode", 5);

// Remote Settings: sin servidor no hay sincronización al arrancar. Firefox release solo
// respeta esta preferencia con MOZ_REMOTE_SETTINGS_DEVTOOLS=1 (config/x11/90nimbo-firefox).
// Los adjuntos que quedaban (firefox-settings-attachments) eran los fondos de la nueva
// pestaña: se apagan arriba.
pref("services.settings.server", "data:,");
pref("services.settings.poll_interval", 0);
