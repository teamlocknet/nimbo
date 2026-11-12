# security/hardening/3b2 — hardening fino (sysctl y PAM)

Implementa el [ADR-014](../../../docs/adr/ADR-014-hardening-3b2-sysctl-pam.md) para
RF-CORE-04 / HU-04. **Dueño:** Emmanuel (`@Cardozo-Mosquera`).

| Fichero | Destino en el sistema | Qué es |
|---|---|---|
| `sysctl/99-zz-nimbo-hardening.conf` | `/etc/sysctl.d/` y `/usr/share/nimbo/hardening/` | Parámetros del kernel; también es la lista de referencia del verificador |
| `pam/faillock.conf` | `/etc/security/faillock.conf` | 5 fallos en 15 min → 10 min de bloqueo; root no se bloquea |
| `pam/nimbo-faillock`, `pam/nimbo-faillock-preauth` | `/usr/share/pam-configs/` | Perfiles de `pam-auth-update` para `pam_faillock` |
| `verify-hardening.sh` | `/usr/lib/nimbo/verify-hardening` | Verificación de RF-CORE-04 en live e instalado: actualizaciones automáticas, sysctl y PAM |
| `aplicar-en-vm.sh` | — | Aplica y mide (lynis + verificador + herramientas) en una VM de prueba |
| `pruebas/test-verify-hardening.sh` | — | Prueba del verificador con una raíz falsa (sin root) |

## Uso

```
bash security/hardening/3b2/pruebas/test-verify-hardening.sh   # en cualquier Linux o Git Bash
sudo bash security/hardening/3b2/aplicar-en-vm.sh              # SOLO en la VM, con snapshot
sudo bash security/hardening/3b2/verify-hardening.sh           # en la ISO live o el instalado
```

⚠ **PAM puede dejar a un usuario sin poder entrar.** En la VM: snapshot antes, una terminal
de root abierta hasta comprobar el inicio de sesión, y la prueba de bloqueo hecha a mano.

La integración en la ISO (receta de `iso/live-build/`) va en un PR aparte, con checkpoint
de Juan José.
