# comun.sh — funciones compartidas por las pruebas de nimbo-nav (se carga con '.').
# Criterio de "sospechoso" = el de iso/live-build/verify-hermetismo-in-qemu.sh:
# DNS (53), NTP (123), HTTP/HTTPS (80/443) o cualquier SYN TCP. ARP, DHCP y NDP
# link-local son puesta en marcha de la NIC y no cuentan.

interfaz_externa() {
  ip -o route get 1.1.1.1 2>/dev/null | sed -n 's/.* dev \([^ ]*\).*/\1/p'
}

contar() {  # contar <pcap> <filtro-bpf>
  tcpdump -nn -r "$1" "$2" 2>/dev/null | wc -l
}

SOSPECHOSO='udp port 53 or tcp port 53 or udp port 123 or tcp port 80 or tcp port 443 or (tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0)'
