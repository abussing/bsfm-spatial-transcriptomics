"""Supervisor survives worker/child termination and writes durable failure evidence."""
import subprocess
import time
import psutil
from .identities import require,write_json

GiB=1024**3


def preflight(minimum_GiB=8):
    available=psutil.virtual_memory().available
    require(available>=minimum_GiB*GiB,'Resource exclusion: insufficient available RAM headroom')
    return available


def stop_tree(process):
    try:children=psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess:children=[]
    for child in reversed(children):
        try:child.kill()
        except psutil.NoSuchProcess:pass
    if process.poll() is None:process.kill()
    process.wait()
    psutil.wait_procs(children,timeout=5)


def supervised(command,cwd,env,log,record,*,ceiling_GiB=10,poll_seconds=.05,minimum_GiB=8):
    available=preflight(minimum_GiB);started=time.perf_counter();peak=0;peak_children=0;failure=None
    with log.open('w',encoding='utf-8') as stream:
        proc=subprocess.Popen(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
        try:
            while proc.poll() is None:
                parent=psutil.Process();children=parent.children(recursive=True)
                total=parent.memory_info().rss
                for p in children:
                    try:total+=p.memory_info().rss
                    except psutil.NoSuchProcess:pass
                peak=max(peak,total);peak_children=max(peak_children,len(children))
                if total>ceiling_GiB*GiB:
                    failure='process_tree_memory_ceiling';stop_tree(proc);break
                time.sleep(poll_seconds)
        except BaseException:
            stop_tree(proc)
            write_json(record,dict(status='interrupted',command=command,peak_process_tree_bytes=peak,
                maximum_children=peak_children,seconds=time.perf_counter()-started))
            raise
    result=dict(status='pass' if proc.returncode==0 and failure is None else 'failed',
        command=command,returncode=proc.returncode,reason=failure,available_before_bytes=available,
        peak_process_tree_bytes=peak,maximum_children=peak_children,poll_seconds=poll_seconds,
        ceiling_GiB=ceiling_GiB,seconds=time.perf_counter()-started)
    write_json(record,result)
    require(result['status']=='pass',f'Worker failed: {failure or proc.returncode}')
    return result
