import os,subprocess,json,pathlib,datetime,inspect
_original=subprocess.run
def _run(*args,**kwargs):
    r=_original(*args,**kwargs)
    cmd=args[0] if args else kwargs.get('args',[])
    if isinstance(cmd,(list,tuple)) and cmd and pathlib.Path(str(cmd[0])).name=='apt-get':
        def text(x):return x.decode(errors='replace') if isinstance(x,bytes) else x
        row=dict(test=next((f.function for f in inspect.stack() if f.function.startswith('test_real_apt_')),None),argv=list(map(str,cmd)),exit_code=r.returncode,stdout=text(r.stdout),stderr=text(r.stderr),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        with open(os.environ['NIMBO_APT_OBSERVACION'],'a') as f:f.write(json.dumps(row)+'\n')
    return r
subprocess.run=_run
