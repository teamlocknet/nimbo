#!/usr/bin/env python3
"""Valida RF-RED-01 en dos VMs ya arrancadas; guarda evidencia y apaga ambas."""
import argparse
import base64
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import socket
import threading
import time

src=Path(__file__).parent
spec=importlib.util.spec_from_file_location("control",src/"control-vm.py")
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)


def execute(lab,installed=False):
    results=[];lock=threading.Lock();checks=[]
    def call(node,cmd,**kw):
        result=control.rpc(lab,node,dict(cmd=cmd,**kw))
        with lock:
            if cmd=="capture_stop" and result.get("ok"):
                directory=lab/"capturas";directory.mkdir(exist_ok=True)
                files={}
                for iface,data in result["result"].items():
                    raw=base64.b64decode(data);file=directory/(node+"."+iface+".pcap");file.write_bytes(raw)
                    files[iface]=dict(bytes=len(raw),archivo=str(file.relative_to(lab)),
                        marcador_visible=bytes.fromhex("6e696d626f2d6c61622d313233343536") in raw)
                stored=dict(ok=True,result=files)
            else:stored=result
            results.append(dict(node=node,cmd=cmd,response=stored))
            (lab/"resultados.json").write_text(json.dumps(results,indent=2))
        print(node,cmd,json.dumps(stored,ensure_ascii=True),flush=True)
        if not result.get("ok"):raise RuntimeError(node+" "+cmd+" fallo")
        return result["result"]
    def pair(a,b):
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            fa=pool.submit(call,'A',a);fb=pool.submit(call,'B',b)
            return fa.result(),fb.result()
    def passed(name,condition):
        checks.append(dict(check=name,ok=bool(condition)))
        (lab/"comprobaciones.json").write_text(json.dumps(checks,indent=2))
        if not condition:raise RuntimeError("no cumple: "+name)
    try:
        for node in ['A','B']:
            baseline=call(node,'baseline')
            if installed:
                passed(node+':arranque desde instalado',baseline['root_fstype']=='ext4' and not baseline['live_medium_present'])
                passed(node+':red apagada al arrancar instalado',not baseline['physical_global_ipv4'])
                passed(node+':Secure Boot activo',baseline['secure_boot'])
                passed(node+':cifrado LUKS2 activo',baseline['luks2_mapping_active'])
            passed(node+':modulo net integrado','nimbo-net 0.1.0-1' in baseline['versions'])
            passed(node+':nimbo-red corregido','nimbo-red 0.1.1-1' in baseline['versions'])
            passed(node+':hardening vigente',baseline['hardening_rc']==0)
            passed(node+':reposo sin wg',not baseline['wg_present'] and not baseline['wg_config_exists'])
            tor_state=dict(line.split('=',1) for line in baseline['units']['tor.service'].splitlines() if '=' in line)
            for unit,values in baseline['units'].items():
                props=dict(line.split('=',1) for line in values.splitlines() if '=' in line)
                generated=(unit=='tor@default.service' and props.get('UnitFileState')=='enabled-runtime'
                           and tor_state.get('UnitFileState')=='disabled')
                off=props.get('UnitFileState') in ['disabled','static','masked'] or generated
                passed(node+':unidad no arranca sola '+unit,props.get('ActiveState')=='inactive' and off)
            probe=call(node,'alias_probe')
            passed(node+':alias aplicado con set en kernel real',probe['alias_en_set']=='nimbo-lab:probe')
            call(node,'prepare_integrated')
            passed(node+':red off inicial',call(node,'network_off')['rc']==0)
            snapshot=call(node,'network_snapshot')
            passed(node+':sin dhclient tras off',not snapshot['dhclient'].strip())
        identities={}
        for node in ['A','B']:identities[node]=call(node,'network_on')
        before={}
        for node,other,i in [('A','B',1),('B','A',2)]:
            peer=identities[other]
            profile=dict(version=1,address='10.90.0.'+str(i),peer_address='10.90.0.'+str(3-i),
                peer_public_key=peer['public_key'],endpoint=peer['ip'],listen_port=51820,endpoint_port=51820,timeout=10)
            call(node,'profile',perfil=profile)
            before[node]=call(node,'network_snapshot')
            call(node,'capture_start',interface='fisica')
        joins=pair('join','join');passed('handshake y trafico en ambos',all(x['rc']==0 for x in joins))
        for node in ['A','B']:
            report=call(node,'report');v=report['rp_filter'];physical=identities[node]['interfaz']
            passed(node+':rp_filter estricto efectivo',max(int(v['all']),int(v[physical]))==1 and max(int(v['all']),int(v['wg-nimbo']))==1)
            call(node,'capture_start',interface='tunel')
        pings=pair('ping','ping');passed('ping bidireccional',all(x['rc']==0 and '0% packet loss' in x['output'] for x in pings))
        for node in ['A','B']:
            call(node,'capture_stop')
            passed(node+':Tor se niega con VPN',call(node,'tor_on')['rc']!=0)
            state=call(node,'coexistence');passed(node+':VPN conservada y Tor inactivo',state['tor']=='inactive' and any(x['ifname']=='wg-nimbo' for x in state['links']))
        pair('leave','leave')
        for node in ['A','B']:
            after=call(node,'network_snapshot')
            passed(node+':DNS conservado',before[node]['resolv_sha256']==after['resolv_sha256'])
            def defaults(routes):return [x for x in routes if x.get('dst')=='default']
            passed(node+':ruta por defecto conservada',defaults(before[node]['routes'])==defaults(after['routes']))
            passed(node+':sin WG ni ruta de tunel',not any(x.get('dev')=='wg-nimbo' for x in after['routes']))
            passed(node+':Tor arranca sin VPN',call(node,'tor_on')['rc']==0)
            call(node,'leaks')
            passed(node+':join se niega con Tor',call(node,'join')['rc']!=0)
            state=call(node,'coexistence');passed(node+':Tor conservado sin WG',state['tor']=='active' and not any(x['ifname']=='wg-nimbo' for x in state['links']))
            call(node,'leaks');call(node,'leak_log');passed(node+':Tor off',call(node,'tor_off')['rc']==0)
        for index,target in enumerate(['A','B','A'],1):
            other='B' if target=='A' else 'A'
            print('RONDA CONCURRENTE',index,target,flush=True)
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                fa=pool.submit(call,target,'race');fb=pool.submit(call,other,'join');race=fa.result();fb.result()
            passed('ronda '+str(index)+':no ambos modos exitosos',not(race['join']['rc']==0 and race['tor']['rc']==0))
            state=call(target,'coexistence');wg=any(x['ifname']=='wg-nimbo' for x in state['links'])
            passed('ronda '+str(index)+':no coexistencia final',not(state['tor']=='active' and wg))
            call(target,'leaks');call(target,'leak_log')
            for node in ['A','B']:
                call(node,'tor_off');call(node,'leave')
        for node in ['A','B']:
            passed(node+':red off final',call(node,'network_off')['rc']==0)
            final=call(node,'network_snapshot');passed(node+':sin dhclient final',not final['dhclient'].strip())
        print('COMPROBACIONES COMPLETADAS',len(checks),flush=True)
    finally:
        for node in ['A','B']:
            for cmd in ['capture_stop','tor_off','leave','network_off','shutdown']:
                try:call(node,cmd)
                except Exception as e:print('Limpieza',node,cmd,type(e).__name__,flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('lab',type=Path);p.add_argument('--instalado',action='store_true');args=p.parse_args()
    # Sondear sin consumir respuestas parciales del agente.
    for node in ['A','B']:
        for _ in range(150):
            try:
                with socket.socket(socket.AF_UNIX) as sock:
                    sock.settimeout(3);sock.connect(str(args.lab/(node+'.serial.sock')));sock.sendall(b'{"cmd":"ready"}\n')
                    with sock.makefile('r') as stream:ready=json.loads(stream.readline())
                    if ready.get('ok'):break
            except (OSError,ValueError):pass
            time.sleep(2)
        else:raise RuntimeError('VM no lista: '+node)
    execute(args.lab,installed=args.instalado)

if __name__=='__main__':main()
