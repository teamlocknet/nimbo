#!/usr/bin/env python3
"""Comprueba el marcador y el transporte UDP en los PCAP del ensayo."""
import argparse,json,struct
from pathlib import Path

MARKER=bytes.fromhex("6e696d626f2d6c61622d313233343536")

def inspect(path):
    raw=path.read_bytes()
    if raw[:4]!=b"\xd4\xc3\xb2\xa1":raise ValueError("PCAP inesperado")
    if len(raw)<24:raise ValueError("PCAP truncado")
    _,major,minor,_,_,snap,link=struct.unpack('<IHHIIII',raw[:24])
    if (major,minor)!=(2,4) or link not in [1,101]:raise ValueError("enlace PCAP inesperado")
    offset=24;packets=0;markers=0;wg=0
    while offset<len(raw):
        if offset+16>len(raw):raise ValueError("cabecera truncada")
        _,_,size,original=struct.unpack('<IIII',raw[offset:offset+16]);offset+=16
        if size>snap or offset+size>len(raw):raise ValueError("paquete truncado")
        payload=raw[offset:offset+size];offset+=size;packets+=1
        markers+=MARKER in payload
        ip=payload
        if link==1:
            if len(payload)<14:continue
            eth=int.from_bytes(payload[12:14],'big');start=14
            if eth==0x8100 and len(payload)>=18:eth=int.from_bytes(payload[16:18],'big');start=18
            if eth!=0x800:continue
            ip=payload[start:]
        if len(ip)>=20 and ip[0]>>4==4 and ip[9]==17:
            start=(ip[0]&15)*4
            if start>=20 and len(ip)>=start+8:
                ports=struct.unpack('>HH',ip[start:start+4]);wg+=51820 in ports
    return dict(bytes=len(raw),linktype=link,packets=packets,marker_packets=markers,udp_51820_packets=wg)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('lab',type=Path);args=p.parse_args()
    results={}
    for node in ['A','B']:
        files=sorted((args.lab/'capturas').glob(node+'.*.pcap'))
        if len(files)!=2:raise ValueError('faltan capturas de '+node)
        values={f.name:inspect(f) for f in files}
        tunnel=values[node+'.wg-nimbo.pcap'];physical=next(v for k,v in values.items() if k!=node+'.wg-nimbo.pcap')
        if not (tunnel['marker_packets']>0 and physical['marker_packets']==0 and physical['udp_51820_packets']>0):
            raise ValueError('marcador/transporte no cumple en '+node)
        results[node]=values
    (args.lab/'ANALISIS-PCAP.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
