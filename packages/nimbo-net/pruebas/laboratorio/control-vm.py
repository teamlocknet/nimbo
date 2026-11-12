#!/usr/bin/env python3
"""Envia una accion de laboratorio por socket local, sin login ni credenciales."""
import json
import socket
import sys
from pathlib import Path


def rpc(lab,node,request):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(480);s.connect(str(Path(lab)/(node+".serial.sock")))
        s.sendall((json.dumps(request)+"\n").encode())
        with s.makefile("r") as f:
            return json.loads(f.readline())


if __name__=="__main__":
    print(json.dumps(rpc(sys.argv[1],sys.argv[2],json.loads(sys.argv[3])),ensure_ascii=False))
