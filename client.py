"""Runs inside the network-isolated container; outputs only captured measurements."""
import json, sys, time, urllib.request

def post(endpoint, payload):
    req=urllib.request.Request('http://127.0.0.1:8080/'+endpoint, None if endpoint=='health' else json.dumps(payload).encode(),{'Content-Type':'application/json'})
    return urllib.request.urlopen(req,timeout=7200)

def main():
    job=json.load(sys.stdin)
    if job['endpoint']!='completion':
        with post(job['endpoint'],job['payload']) as r: print(r.read().decode())
        return
    payload=job['payload']; payload['stream']=True
    start=time.perf_counter(); events=[]; arrivals=[]; content=[]; ids=[]
    with post('completion',payload) as r:
        for raw in r:
            if not raw.startswith(b'data: '): continue
            data=raw[6:].strip()
            if data==b'[DONE]': continue
            e=json.loads(data); events.append(e)
            if e.get('tokens'):
                ids.extend(e['tokens']); arrivals.extend([time.perf_counter()-start]*len(e['tokens']))
            content.append(e.get('content',''))
    assert events[-1].get('stop') and 'timings' in events[-1]
    print(json.dumps({'output':''.join(content),'token_ids':ids,'arrivals_s':arrivals,'total_s':time.perf_counter()-start,'final':events[-1]}))

if __name__=='__main__': main()
