"""Serial, resumable CPU measurements. Completed blocks are never replaced."""
import contextlib, datetime, hashlib, json, math, os, pathlib, signal, subprocess, sys, time
from setup import WORK, IMAGE
DEMO=WORK/'demo'
NAME='vk-kvcache-measure'
PROV=json.loads((WORK/'provenance/models.json').read_text()) if (WORK/'provenance/models.json').exists() else {}

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def load(): return os.getloadavg()[0]
def clean(s):
    return s.replace(str(WORK.parents[2]),'<workspace>')
def docker(*args, data=None):
    p=subprocess.run(['docker',*args],input=data,capture_output=True,text=True)
    if p.returncode: raise RuntimeError(clean(p.stderr))
    return p.stdout.strip()
def save(path, row):
    with path.open('a') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
def api(endpoint,payload):
    raw=docker('exec','-i',NAME,'python3','/demo/client.py',data=json.dumps({'endpoint':endpoint,'payload':payload}))
    return json.loads(raw)
def complete(prompt,n,**kw):
    started=utc(); before=load()
    payload=dict(prompt=prompt,n_predict=n,temperature=0,seed=12648430,cache_prompt=False,return_tokens=True)
    payload.update(kw)
    result=api('completion',payload)
    return dict(started_utc=started,loadavg_1m=before,**result)

@contextlib.contextmanager
def server(block,role='main',ctx=32768,k='f16',v='f16',parallel=1):
    target='/models/Qwen3-4B-Q4_K_M.gguf' if role=='main' else '/contrast/qwen3.5-4b-q4_k_m.gguf'
    args=['run','-d','--name',NAME,'--pull','never','--network','none','--memory','44g','--memory-swap','44g',
          '--entrypoint','/usr/bin/nice','-v',str(WORK/'models')+':/models:ro','-v',str(WORK.parent/'specdec/models')+':/contrast:ro',
          '-v',str(DEMO)+':/demo:ro','-e','OMP_NUM_THREADS=8','-e','OPENBLAS_NUM_THREADS=8',IMAGE,'-n','10','/app/llama-server',
          '-m',target,'-ngl','0','-t','8','-tb','8','-c',str(ctx),'--parallel',str(parallel),'--threads-http','1',
          '--host','127.0.0.1','--port','8080','-fa','on','-ctk',k,'-ctv',v,'--cache-ram','0','--no-warmup','--no-context-shift','-lv','4']
    row=dict(block=block,role=role,ctx=ctx,k=k,v=v,parallel=parallel,started_utc=utc(),loadavg_1m=load(),command=[clean(a) for a in ['docker',*args]])
    live=False
    try:
        docker(*args); live=True
        for _ in range(240):
            try:
                api('health',{})
                break
            except Exception:
                if docker('inspect','--format','{{.State.Running}}',NAME)!='true': raise RuntimeError('Server exited; see log')
                time.sleep(1)
        else: raise RuntimeError('Readiness timeout')
        print(block+' ready',flush=True)
        yield row
        row['complete']=True
    finally:
        if live:
            try:
                status=docker('exec',NAME,'cat','/proc/1/status')
                row['rss_KiB']={s.split(':')[0]:int(s.split()[1]) for s in status.splitlines() if s.startswith(('VmHWM:','VmRSS:'))}
                pid=docker('inspect','--format','{{.State.Pid}}',NAME)
                # Container cgroup peak includes file cache and all helper processes, unlike process RSS.
                cgroup=pathlib.Path('/proc/'+pid+'/cgroup').read_text().strip().split('::')[-1]
                peak=pathlib.Path('/sys/fs/cgroup')/cgroup.lstrip('/')/'memory.peak'
                row['cgroup_peak_bytes']=int(peak.read_text())
            except Exception as e: row['memory_error']=clean(str(e))
            logs=subprocess.run(['docker','logs',NAME],capture_output=True,text=True)
            (DEMO/'logs'/f'{block}.log').write_text(clean(logs.stdout+logs.stderr))
            docker('rm','-f',NAME)
        row['finished_utc']=utc()
        save(DEMO/'results/blocks.jsonl',row)

def done(block):
    p=DEMO/'results/blocks.jsonl'
    return p.exists() and any(r.get('complete') and r['block']==block for r in map(json.loads,p.read_text().splitlines()))

def fixtures():
    p=DEMO/'fixtures/tasks.json'
    if p.exists(): return json.loads(p.read_text())
    # All questions share one authored document; only the question suffix changes.
    filler='The storage room has pale walls and a clean floor. A narrow shelf holds plain empty boxes. Each box stays closed until the next inspection. The inspection follows the same routine every day.\n'
    unit=api('tokenize',{'content':filler,'add_special':False})['tokens']
    lead='Read this storage ledger. Answer the question after the ledger using only its three-digit code.\n<ledger>\n'
    a=api('tokenize',{'content':lead,'add_special':True})['tokens']
    facts=[]; questions=[]
    for i in range(20):
        key=f'vault-{i+1:02d}'; answer=f'{(i*137+419)%1000:03d}'
        tail=f'</ledger>\nQuestion: What is the access code for {key}? Return only the code.\nAnswer:'
        fact=f'\nThe access code for {key} is {answer}. This is the only assigned code for that vault.\n'
        z=api('tokenize',{'content':tail,'add_special':False})['tokens']
        f=api('tokenize',{'content':fact,'add_special':False})['tokens']
        facts.append(dict(key=key,answer=answer,text=fact,tokens=f))
        questions.append(z)
    common_length=24576-max(map(len,questions))
    budget=common_length-len(a)-sum(len(f['tokens']) for f in facts)
    bg=(unit*math.ceil(budget/len(unit)))[:budget]
    common=list(a); cursor=0; depths=[]
    for i,f in enumerate(facts):
        at=round(budget*(i+0.5)/20)
        common.extend(bg[cursor:at]); depths.append(len(common)/24576)
        common.extend(f['tokens']); cursor=at
    common.extend(bg[cursor:]); assert len(common)==common_length
    newline=api('tokenize',{'content':'\n','add_special':False})['tokens']; assert len(newline)==1
    tasks=[]
    for i,(f,z) in enumerate(zip(facts,questions)):
        ids=common+newline*(24576-len(common)-len(z))+z
        assert len(ids)==24576
        tasks.append(dict(id=f'T{i+1:02d}',key=f['key'],answer=f['answer'],depth=depths[i],prompt=ids,shared_document_tokens=common_length))
    p.write_text(json.dumps(tasks)+'\n')
    (DEMO/'fixtures/authored-text.json').write_text(json.dumps({'filler':filler,'lead':lead,'facts':[{k:v for k,v in f.items() if k!='tokens'} for f in facts],'description':'One fixed document, twenty authored retrieval checks, not a benchmark.','question_template':'Question: What is the access code for vault-NN? Return only the code. Answer:'})+'\n')
    return tasks

def measure_a():
    for role in ['main','contrast']:
        fields=next(m for m in PROV['models'] if m['role']==role)['metadata']['fields']
        arch=fields['general.architecture']; maximum=fields[arch+'.context_length']
        for ctx in [4096,16384,32768,65536,131072]:
            if ctx>maximum: continue
            block=f'A-{role}-{ctx}'
            if done(block): continue
            with server(block,role,ctx): pass
    block='D-parallel4'
    if not done(block):
        with server(block,ctx=32768,parallel=4): pass

def measure_b():
    for repeat in range(1,4):
        block=f'B-r{repeat}'
        if done(block): continue
        with server(block,ctx=8192):
            if (DEMO/'fixtures/b-prompt.json').exists():
                prompt=json.loads((DEMO/'fixtures/b-prompt.json').read_text())
            else:
                text=('The empty boxes are sorted by size. Each shelf has enough room for another box. '*500)
                prompt=api('tokenize',{'content':text,'add_special':True})['tokens'][:4096]
                assert len(prompt)==4096
                (DEMO/'fixtures/b-prompt.json').write_text(json.dumps(prompt)+'\n')
            # Rotate order to expose warm/cold and background-load differences.
            for mode in (['reuse','no-reuse'] if repeat%2 else ['no-reuse','reuse']):
                path=DEMO/'results'/f'{block}-{mode}.jsonl'
                assert not path.exists(),'Partial B evidence retained; inspect before resuming'
                if mode=='reuse':
                    result=complete(prompt,64,ignore_eos=True)
                    assert len(result['token_ids'])==64
                    save(path,dict(repeat=repeat,mode=mode,**result))
                else:
                    ids=[]
                    for step in range(64):
                        result=complete(prompt+ids,1,ignore_eos=True)
                        assert len(result['token_ids'])==1
                        ids.extend(result['token_ids'])
                        save(path,dict(repeat=repeat,mode=mode,step=step+1,prompt_tokens=len(prompt)+step,**result))
                        print(f'{block} no-reuse {step+1}/64',flush=True)

def measure_c():
    for k,v in [('f16','f16'),('q8_0','q8_0'),('q4_0','q4_0'),('q8_0','q4_0')]:
        block=f'C-{k}-{v}'
        if done(block): continue
        with server(block,k=k,v=v):
            tasks=fixtures()
            path=DEMO/'results'/f'{block}.jsonl'
            assert not path.exists(),'Partial C evidence retained; inspect before resuming'
            for i,task in enumerate(tasks):
                # Raw completion keeps template length fixed; continuations may include reasoning text.
                r=complete(task['prompt'],32,cache_prompt=i>0)
                save(path,dict(id=task['id'],expected=task['answer'],depth=task['depth'],prompt_tokens=len(task['prompt']),shared_document_tokens=task['shared_document_tokens'],cache_prompt=i>0,**r))
                print(block+' '+task['id']+' saved',flush=True)

def main():
    signal.signal(signal.SIGTERM,lambda *_:sys.exit(143))
    measure_a(); measure_b(); measure_c()
    print('All measurements complete',flush=True)
if __name__=='__main__': main()
