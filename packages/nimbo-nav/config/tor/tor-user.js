// nimbo-nav — perfil Tor de firefox-esr (ADR-012, RF-NAV-02).
// nimbo-navegar-tor copia este fichero como user.js del perfil Tor cada vez que lo abre.
// Si Tor no responde, el navegador NO cae a conexión directa (failover_direct = false).

// Todo por el SOCKS5 de tor, con resolución DNS dentro del túnel
user_pref("network.proxy.type", 1);
user_pref("network.proxy.socks", "127.0.0.1");
user_pref("network.proxy.socks_port", 9050);
user_pref("network.proxy.socks_version", 5);
user_pref("network.proxy.socks_remote_dns", true);
user_pref("network.proxy.no_proxies_on", "");
user_pref("network.proxy.failover_direct", false);
user_pref("network.proxy.allow_hijacking_localhost", true);

// Vías conocidas de fuga fuera del proxy
user_pref("media.peerconnection.enabled", false);
user_pref("network.dns.disableIPv6", true);
user_pref("network.trr.mode", 5);
user_pref("network.dns.disablePrefetch", true);
user_pref("network.prefetch-next", false);
user_pref("network.predictor.enabled", false);
user_pref("network.http.speculative-parallel-limit", 0);
user_pref("browser.send_pings", false);
user_pref("security.OCSP.enabled", 0);
user_pref("network.captive-portal-service.enabled", false);
user_pref("network.connectivity-service.enabled", false);

// Sesión sin rastro en disco
user_pref("browser.privatebrowsing.autostart", true);
user_pref("browser.cache.disk.enable", false);

// Huella del navegador (ADR-012 aceptado, #45): reduce la brecha con Tor Browser, no la cierra
user_pref("privacy.resistFingerprinting", true);
user_pref("privacy.resistFingerprinting.letterboxing", true);
