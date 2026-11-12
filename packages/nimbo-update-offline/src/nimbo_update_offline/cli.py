"""nimbo-update-offline — actualiza nimbo sin conexión, solo con paquetes firmados.

  nimbo-update-offline verificar <lote>        comprueba firma y sumas (no instala)
  sudo nimbo-update-offline instalar <lote>    copia, verifica la copia e instala sin red
                                               (SIEMPRE con el anillo de nimbo: no admite
                                               otro; revisión de #49)
  nimbo-update-offline preparar <lote> --clave <id>
                                               (equipo con la clave) escribe MANIFIESTO y
                                               lo firma con gpg

Códigos de salida: 0 aceptado/instalado · 1 rechazado o fallo · 2 uso incorrecto o sin root.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from .verificar import ANILLO, NOMBRE_VALIDO, verificar


def _ejecutar(argv: list[str]) -> None:
    subprocess.run(argv, check=True)


def _root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


def cmd_verificar(lote: Path, anillo: Path) -> int:
    v = verificar(lote, anillo)
    print(("ACEPTADO: " if v.aceptado else "RECHAZADO: ") + v.motivo)
    for p in v.paquetes:
        print(f"  - {p.name}")
    return 0 if v.aceptado else 1


def cmd_instalar(lote: Path, anillo: Path, ejecutar: Callable[[list[str]], None]) -> int:
    # Se copia el lote a un directorio propio y se verifica LA COPIA: así nadie puede
    # cambiar un .deb en la USB entre la verificación y la instalación.
    with tempfile.TemporaryDirectory(prefix="nimbo-update-") as tmp:
        copia = Path(tmp)
        for p in Path(lote).iterdir():
            if p.is_file() and (p.name in ("MANIFIESTO", "MANIFIESTO.asc") or p.suffix == ".deb"):
                shutil.copy2(p, copia / p.name)
        v = verificar(copia, anillo)
        if not v.aceptado:
            print(f"RECHAZADO: {v.motivo}. No se instaló nada.")
            return 1
        print(f"ACEPTADO: {v.motivo}. Instalando sin red...")
        # apt SIN ninguna fuente remota: no puede descargar nada (lo que no venga en el lote o
        # no esté ya instalado, falla) y conserva su negativa a bajar de versión sin
        # --allow-downgrades. No se usa --no-download: con .deb locales, el apt de bookworm
        # falla con "Internal Error, Pathname to install is not absolute" (medido en VM, 11-nov).
        fuentes = Path(tmp) / "apt"
        (fuentes / "sources.list.d").mkdir(parents=True)
        (fuentes / "sources.list").write_text("", encoding="utf-8")
        try:
            ejecutar(["apt-get", "install", "-y",
                      "-o", f"Dir::Etc::sourcelist={fuentes / 'sources.list'}",
                      "-o", f"Dir::Etc::sourceparts={fuentes / 'sources.list.d'}",
                      *[str(p) for p in v.paquetes]])
        except subprocess.CalledProcessError as e:
            print(f"nimbo-update-offline: apt-get falló (código {e.returncode}).")
            return 1
    print("nimbo-update-offline: actualización instalada.")
    return 0


def cmd_preparar(lote: Path, clave: str) -> int:
    lote = Path(lote)
    debs = sorted(p for p in lote.glob("*.deb"))
    if not debs:
        print("nimbo-update-offline: no hay .deb en el lote")
        return 1
    for p in debs:
        if not NOMBRE_VALIDO.match(p.name):
            print(f"nimbo-update-offline: nombre no permitido: {p.name}")
            return 1
    lineas = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in debs]
    (lote / "MANIFIESTO").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    subprocess.run(["gpg", "--batch", "--yes", "--local-user", clave, "--armor",
                    "--detach-sign", "--output", str(lote / "MANIFIESTO.asc"),
                    str(lote / "MANIFIESTO")], check=True)
    print(f"Lote preparado y firmado: {len(debs)} paquetes. Verifícalo con: "
          f"nimbo-update-offline verificar {lote}")
    return 0


def main(argv: list[str] | None = None, es_root: Callable[[], bool] = _root,
         ejecutar: Callable[[list[str]], None] = _ejecutar,
         anillo_instalar: Path = ANILLO) -> int:
    # anillo_instalar solo lo cambian las pruebas (parámetro de Python). Desde la línea de
    # órdenes, instalar no admite --anillo: un lote podría traer su propia clave y pedir
    # que se use, y saltarse RF-UPD-01.
    p = argparse.ArgumentParser(prog="nimbo-update-offline", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="accion", required=True)
    s = sub.add_parser("verificar")
    s.add_argument("lote", type=Path)
    s.add_argument("--anillo", type=Path, default=ANILLO,
                   help="anillo de confianza para COMPROBAR (por defecto, el de nimbo); "
                        "no instala nada")
    s = sub.add_parser("instalar")
    s.add_argument("lote", type=Path)
    s = sub.add_parser("preparar")
    s.add_argument("lote", type=Path)
    s.add_argument("--clave", required=True, help="identificador de la clave GPG de firma")
    args = p.parse_args(sys.argv[1:] if argv is None else argv)

    if args.accion == "verificar":
        return cmd_verificar(args.lote, args.anillo)
    if args.accion == "instalar":
        if not es_root():
            print(f"nimbo-update-offline: necesita privilegios. Usa: sudo nimbo-update-offline instalar {args.lote}")
            return 2
        return cmd_instalar(args.lote, Path(anillo_instalar), ejecutar)
    return cmd_preparar(args.lote, args.clave)


if __name__ == "__main__":
    sys.exit(main())
