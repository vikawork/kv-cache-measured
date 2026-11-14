"""Generate the report from retained JSONL rows and exact server-log evidence."""
import hashlib, ipaddress, json, math, os, pathlib, re, statistics
from setup import WORK, sha
D=WORK/'demo'

def rows(path): return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]
def med(xs): return statistics.median(xs)
def firstdiff(a,b): return next((i+1 for i,(x,y) in enumerate(zip(a,b)) if x!=y), None if len(a)==len(b) else min(len(a),len(b))+1)
def table(headers,rs):
    def cell(s): return str(s).replace('|','\\|').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(cell,r))+' |' for r in rs])+'\n'
def main():
    provenance=json.loads((WORK/'provenance/models.json').read_text())
    blocks=rows(D/'results/blocks.jsonl')
    assert all(b.get('complete') for b in blocks)
    assert len({b['block'] for b in blocks})==len(blocks)
    evidence={}; formulas=[]
    for m in provenance['models']:
        f=m['metadata']['fields']; a=f['general.architecture']
        active=f[a+'.block_count']-f.get(a+'.nextn_predict_layers',0)
        layers=sum(i<active for i in f['attention_layer_indices'])
        nk=f[a+'.attention.head_count_kv']; h=f[a+'.attention.key_length']
        assert h==f[a+'.attention.value_length']
        formulas.append(dict(role=m['role'],gguf_layers=f[a+'.block_count'],runtime_layers=active,kv_layers=layers,heads=f[a+'.attention.head_count'],kv_heads=nk,head_size=h,bpt=2*layers*nk*h*2,weights=m['bytes'],crossover_tokens=m['bytes']/(2*layers*nk*h*2)))
    for b in blocks:
        log=D/'logs'/f'{b["block"]}.log'; lines=log.read_text().splitlines()
        hits=[(i+1,s) for i,s in enumerate(lines) if 'CPU KV buffer size' in s]
        assert len(hits)==1,(b['block'],hits)
        line,text=hits[0]; size=float(re.search(r'=\s*([\d.]+) MiB',text)[1])*2**20
        b['kv_bytes']=int(size); b['kv_evidence']=f'logs/{log.name}:{line}'
        unit={'f16':2,'q8_0':34/32,'q4_0':18/32}
        f=next(f for f in formulas if f['role']==b['role'])
        expected=b['ctx']*f['kv_layers']*f['kv_heads']*f['head_size']*(unit[b['k']]+unit[b['v']])
        assert size==expected,(b['block'],size,expected)
        b['expected_bytes']=int(expected)
        evidence[b['block']]=[(i+1,s) for i,s in enumerate(lines) if any(x in s for x in ['KV buffer size','RS buffer size','n_ctx_slot','new slot','n_layer '])]
        assert b['rss_KiB']['VmHWM']>0 and b['cgroup_peak_bytes']<48_000_000_000
    bs=[]
    for repeat in range(1,4):
        a=rows(D/f'results/B-r{repeat}-reuse.jsonl'); n=rows(D/f'results/B-r{repeat}-no-reuse.jsonl')
        assert len(a)==1 and len(n)==64 and [r['step'] for r in n]==list(range(1,65))
        a=a[0]; ni=[t for r in n for t in r['token_ids']]
        assert len(a['token_ids'])==len(ni)==64
        # All no-reuse requests must evaluate their entire growing prompt.
        assert all(r['final']['timings']['prompt_n']==4096+i for i,r in enumerate(n))
        assert a['final']['timings']['prompt_n']==4096
        bs.append(dict(repeat=repeat,reuse_total_s=a['total_s'],no_reuse_total_s=sum(r['total_s'] for r in n),reuse_first_s=a['arrivals_s'][0],reuse_64th_s=a['arrivals_s'][63],no_reuse_first_s=n[0]['total_s'],no_reuse_64th_s=n[63]['total_s'],no_reuse_64th_cumulative_s=sum(r['total_s'] for r in n),identical=a['output']==''.join(r['output'] for r in n),identical_ids=a['token_ids']==ni,first_difference=firstdiff(a['token_ids'],ni)))
    cs={}; base=rows(D/'results/C-f16-f16.jsonl')
    fixtures=json.loads((D/'fixtures/tasks.json').read_text())
    assert len(fixtures)==20 and len({f['key'] for f in fixtures})==20
    for condition in ['f16-f16','q8_0-q8_0','q4_0-q4_0','q8_0-q4_0']:
        data=rows(D/f'results/C-{condition}.jsonl')
        assert len(data)==20 and [r['id'] for r in data]==[f['id'] for f in fixtures]
        pairs=[]
        for i,(r,ref,f) in enumerate(zip(data,base,fixtures)):
            timing=r['final']['timings']
            assert r['prompt_tokens']==24576 and timing['prompt_n']+timing['cache_n']==24576
            if i==0: assert not r['cache_prompt'] and timing['prompt_n']==24576 and timing['cache_n']==0
            else: assert r['cache_prompt'] and timing['cache_n']>=r['shared_document_tokens']-1
            pairs.append(dict(id=r['id'],expected=f['answer'],output=r['output'],correct=r['output'].strip()==f['answer'],first_line_correct=r['output'].strip().splitlines()[0]==f['answer'] if r['output'].strip() else False,same_text=r['output']==ref['output'],first_difference=firstdiff(ref['token_ids'],r['token_ids']),prompt_tps=r['final']['timings']['prompt_per_second'],generation_tps=r['final']['timings']['predicted_per_second'],load=r['loadavg_1m'],token_limit=r['final'].get('stop_type')=='limit'))
            pairs[-1].update(evaluated_prompt_tokens=timing['prompt_n'],reused_tokens=timing['cache_n'])
        cs[condition]=dict(correct=sum(p['correct'] for p in pairs),first_line_correct=sum(p['first_line_correct'] for p in pairs),exact_matches=sum(p['same_text'] for p in pairs),prompt_tps=data[0]['final']['timings']['prompt_per_second'],generation_tps=med([p['generation_tps'] for p in pairs]),pairs=pairs)
    capacities=[]
    f=formulas[0]; q8=next(b for b in blocks if b['block']=='C-q8_0-q8_0')['kv_bytes']/32768
    for unit,mult in [('GB',10**9),('GiB',2**30)]:
        for total in [16,64]:
            for cache,bpt in [('f16',f['bpt']),('q8_0',q8)]:
                capacities.append(dict(unit=unit,budget=total,cache=cache,bytes_per_token=bpt,conversations=math.floor((total*mult-f['weights'])/(8192*bpt))))
    formula_rows=[dict(role=r['role'],equation=f'2 * {r["kv_layers"]} * {r["kv_heads"]} * {r["head_size"]} * 2 = {r["bpt"]} bytes/token',source='../provenance/models.json',**{k:r[k] for k in ['bpt','weights','crossover_tokens']}) for r in formulas]
    (D/'results/formulas.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in formula_rows))
    comparison=[]
    for i,r in enumerate(cs['q4_0-q4_0']['pairs']):
        ref=base[i]['output'].strip().splitlines()[:1]
        result=r['output'].strip().splitlines()[:1]
        comparison.append(f'{r["id"]} expected={r["expected"]} f16_first_line={ref!r} q4_0_first_line={result!r} first_differing_token={r["first_difference"]}')
    (D/'logs/C-answer-comparison.log').write_text('\n'.join(comparison)+'\n')
    for mode in ['reuse','no-reuse']:
        lines=[]
        for r in bs:
            prefix='reuse' if mode=='reuse' else 'no_reuse'
            end='64th_s'
            label='cumulative' if mode=='reuse' else 'step'
            lines.append(f'repeat={r["repeat"]} total_s={r[prefix+"_total_s"]:.6f} token1_s={r[prefix+"_first_s"]:.6f} token64_{label}_s={r[prefix+"_"+end]:.6f} identical_text={r["identical"]} identical_ids={r["identical_ids"]}')
        (D/'logs'/f'B-{mode}-timing.log').write_text('\n'.join(lines)+'\n')
    summary=dict(formulas=formulas,blocks=blocks,reuse=bs,quantized=cs,capacities=capacities,evidence=evidence)
    summary['provenance_sha256']={p.name:sha(p) for p in sorted((WORK/'provenance').glob('*.json'))}
    summary['input_sha256']={str(p.relative_to(D)):sha(p) for p in sorted(D.rglob('*')) if p.is_file() and (p.suffix in ['.jsonl','.log','.py'] or p.parent.name=='fixtures')}
    (D/'results/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    out=[]
    def emit(s=''): out.append(s+'\n')
    emit('# KV cache: the memory and reuse measurement\n')
    emit('Question: how much memory does cached attention cost, what computation does it save, and what changes when its stored vectors use fewer bits?\n')
    emit('## Headline figures\n')
    emit(f'The main model allocates {f["bpt"]:,} bytes of f16 KV cache per token.\n')
    biggest=next(b for b in blocks if b['block']=='A-main-32768')
    emit(f'At 32,768 tokens, its f16 KV cache is {biggest["kv_bytes"]/2**30:.1f} GiB.\n')
    boundary=min(b['ctx'] for b in blocks if b['role']=='main' and b['k']==b['v']=='f16' and b['kv_bytes']>f['weights'])
    emit(f'The main model’s f16 cache already outweighs its GGUF weight file at a measured context of {boundary:,} tokens.\n')
    emit(f'The hybrid contrast allocates {formulas[1]["bpt"]:,} bytes of f16 KV cache per token.\n')
    emit(f'Cached generation took a median of {med([r["reuse_total_s"] for r in bs]):.3f} seconds, including processing the 4,096-token prompt and generating 64 tokens.\n')
    emit(f'Recomputing the growing prompt took a median of {med([r["no_reuse_total_s"] for r in bs]):.3f} seconds for 64 tokens.\n')
    emit(f'The cached and recomputed outputs matched on {sum(r["identical"] for r in bs)} of the three repeats.\n')
    for condition in ['q8_0-q8_0','q4_0-q4_0','q8_0-q4_0']:
        b=next(b for b in blocks if b['block']=='C-'+condition)
        emit(f'The {condition} cache allocated {b["kv_bytes"]/2**30:.6f} GiB at 32,768 tokens.\n')
        emit(f'The {condition} cache passed {cs[condition]["correct"]} of 20 strict answer-only checks.\n')
        emit(f'The {condition} cache returned the correct code on its first answer line in {cs[condition]["first_line_correct"]} of 20 authored retrieval checks.\n')
    emit('The four-slot server allocated 8,192 context tokens per slot.\n')
    emit('## Setup and provenance\n')
    emit('Machine: a desktop processor with 16 cores. CPU only; nice 10; eight inference and batch threads; one server at a time. Containers use networking disabled, no exposed ports, and a 44 GiB cgroup limit with no swap. Peak cgroup memory is recorded independently of process peak RSS.\n')
    emit('Image: `'+provenance['image']+'`.\n')
    emit('The publisher GGUF for Qwen3-4B supplies a dense, full-attention GQA model in the requested size range without conversion. Q4_K_M keeps weight memory small enough to observe cache/file crossover within its native context limit. The contrast reuses the previous demo’s verified local Q4_K_M conversion. Publisher names below are necessary model provenance; private identity is excluded.\n')
    emit(table(['Role','Publisher repository','Revision','GGUF bytes','SHA-256'],[[m['role'],m['repository'],m['revision'],m['bytes'],m['sha256']] for m in provenance['models']]))
    emit('Main download: `'+provenance['download_url']+'`. Gated status and license: `../provenance/publisher.json`. Contrast conversion provenance: `.studio/ai-channel/specdec/provenance/setup.json`; no conversion performed by this job.\n')
    emit(f'Measurement interval: {blocks[0]["started_utc"]} through {blocks[-1]["finished_utc"]}. Seed 12648430; temperature zero; raw token-ID completions. B ignores EOS to measure exactly 64 steps. C permits EOS and caps at 32 generated tokens. Flash attention is on for every condition; server logs confirm effective settings.\n')
    emit('## Metadata and formula\n')
    emit(table(['Role','GGUF layers','Runtime layers','KV layers','Attention heads','KV heads','Head size','f16 bytes/token'],[[r[k] for k in ['role','gguf_layers','runtime_layers','kv_layers','heads','kv_heads','head_size','bpt']] for r in formulas]))
    for i,r in enumerate(formulas):
        emit(f'{r["role"]}: 2 × {r["kv_layers"]} × {r["kv_heads"]} × {r["head_size"]} × 2 = {r["bpt"]:,} bytes/token. Exact formula evidence: `results/formulas.jsonl:{i+1}`. Metadata: `../provenance/models.json`; runtime allocation is confirmed in the logs below.\n')
        emit(f'{r["role"]} file/cache equality by arithmetic: {r["weights"]:,} / {r["bpt"]:,} = {r["crossover_tokens"]:.6f} tokens. The two boundary runs bracket this value at 256-token allocation boundaries.\n')
    emit('The contrast stores 33 blocks in GGUF, including one next-token prediction block. The server uses 32 runtime layers: eight full-attention layers and 24 recurrent layers. Its separate recurrent-state allocation is 50.25 MiB for one slot and does not grow with context in this sweep. Counting every GGUF block as a KV layer gives the wrong prediction.\n')
    emit('q8_0 stores 32 values plus a two-byte scale in 34 bytes; q4_0 uses 18 bytes per block of 32 values. Replace bytes/element by 34/32 and 18/32, respectively. These include block-scale overhead. All measured allocations below exactly equal the corresponding formula.\n')
    emit('## A. Growth and every server run\n')
    emit('The main model’s GGUF native limit is 40,960 tokens. The requested 65,536 and 131,072 main-model contexts are skipped. A supplementary 40,960-token run reaches its native limit. Contrast runs cover every requested size through 131,072.\n')
    emit('A and D peaks cover startup allocation only. They do not measure filling the entire context. Peak RSS is the server process kernel VmHWM; cgroup peak includes helper processes and file-cache charges, and can be smaller than process RSS because mapped pages can be counted more than once in RSS.\n')
    emit(table(['Block','Context','K/V','KV MiB','Formula bytes','Peak RSS KiB','Cgroup peak bytes','Load at server start','Evidence'],[[b['block'],b['ctx'],b['k']+'/'+b['v'],b['kv_bytes']/2**20,b['expected_bytes'],b['rss_KiB']['VmHWM'],b['cgroup_peak_bytes'],b['loadavg_1m'],b['kv_evidence']] for b in blocks]))
    emit('## B. What cache reuse saves\n')
    emit('Both paths start with exactly 4,096 identical token IDs. Normal decoding processes that prompt once and generates 64 steps. No-reuse sends the original prompt plus its own generated token IDs afresh on each of 64 requests, with cache_prompt=false and n_predict=1. Server prompt_n is checked at every step: 4,096 through 4,159. No prompt text is retokenized between steps.\n')
    emit('Times below are measured inside the container-side HTTP client. Total no-reuse time sums HTTP request durations and excludes Python/docker launch gaps; normal time is one HTTP request. First and 64th latency are individual step latency for no-reuse. Normal token 64 is cumulative arrival time; its incremental latency is reported separately below. Timing does not include server startup. Order alternates across repeats.\n')
    emit(table(['Repeat','Reuse total s','No reuse total s','Reuse token1 s','Reuse token64 cumulative s','No reuse token1 s','No reuse token64 step s','Exact text','Exact IDs','First differing token'],[[r[k] for k in ['repeat','reuse_total_s','no_reuse_total_s','reuse_first_s','reuse_64th_s','no_reuse_first_s','no_reuse_64th_s','identical','identical_ids','first_difference']] for r in bs]))
    for repeat in range(1,4):
        a=rows(D/f'results/B-r{repeat}-reuse.jsonl')[0]
        emit(f'Repeat {repeat}: normal token 64 incremental arrival latency {a["arrivals_s"][63]-a["arrivals_s"][62]:.6f} s. Evidence: `results/B-r{repeat}-reuse.jsonl:1`; no-reuse: `results/B-r{repeat}-no-reuse.jsonl:1` and `:64`.\n')
    emit(table(['Mode','Median total s','Median token1 s','Median token64 (cumulative reuse / step no-reuse) s'],[['reuse',med([r['reuse_total_s'] for r in bs]),med([r['reuse_first_s'] for r in bs]),med([r['reuse_64th_s'] for r in bs])],['no-reuse',med([r['no_reuse_total_s'] for r in bs]),med([r['no_reuse_first_s'] for r in bs]),med([r['no_reuse_64th_s'] for r in bs])]]))
    incremental=[rows(D/f'results/B-r{i}-reuse.jsonl')[0]['arrivals_s'] for i in range(1,4)]
    emit(f'Normal token 64 median incremental arrival latency: {med([a[63]-a[62] for a in incremental]):.6f} s. No-reuse token 64 median cumulative time: {med([r["no_reuse_64th_cumulative_s"] for r in bs]):.6f} s.\n')
    emit('## C. Quantized cache: authored retrieval checks\n')
    emit('One fixed self-written ledger contains twenty unique vault/code assignments at varied depths, surrounded by neutral filler. Twenty questions each have one checkable answer; every document-plus-question prompt is exactly 24,576 tokens. These are authored checks, not a benchmark. Each fresh cache configuration processes the first question cold; its speed below measures the entire prompt. Subsequent questions reuse the common document prefix, with evaluated and reused token counts shown explicitly. Generation speed is the median over twenty questions. This C protocol measures stored-cache retrieval, while B separately forces full recomputation.\n')
    emit('Strict answer-only correctness strips surrounding whitespace only. First-line correctness checks only the first nonempty answer line, preserving the strict score separately. This secondary score and the shared-document protocol were fixed after observing continuation text in three exploratory f16 outputs, before any quantized-cache output was measured; see fixtures/scoring-policy.json and ../pilot-separate-documents/protocol-change.json. Those exploratory rows remain retained and excluded. Raw completion can retrieve a code and still fail the requested answer-only format. f16 output exact-match compares unmodified text. First difference is one-based emitted token ID, including terminal tokens. An ended sequence differs at its next token.\n')
    emit(table(['K/V','Strict answer-only /20','First answer line /20','Exact f16 text /20','Cold prompt tokens/s (one run)','Median generation tokens/s'],[[c,r['correct'],r['first_line_correct'],r['exact_matches'],r['prompt_tps'],r['generation_tps']] for c,r in cs.items()]))
    emit(table(['Condition','Task','Depth fraction','Expected','Output','Strict','First line','Same f16','First token difference','Evaluated prompt tokens','Reused tokens','Prompt tok/s','Generation tok/s','Load','At limit','Evidence'],[[c,r['id'],fixtures[i]['depth'],r['expected'],repr(r['output']),r['correct'],r['first_line_correct'],r['same_text'],r['first_difference'],r['evaluated_prompt_tokens'],r['reused_tokens'],r['prompt_tps'],r['generation_tps'],r['load'],r['token_limit'],f'results/C-{c}.jsonl:{i+1}'] for c,data in cs.items() for i,r in enumerate(data['pairs'])]))
    emit('## D. Conversations that fit: arithmetic, not a serving benchmark\n')
    emit('floor((budget − GGUF file bytes) / (8,192 × measured cache bytes/token)). GB means decimal 10^9 bytes. GiB figures are included to avoid unit ambiguity. These are upper bounds: compute buffers, weight repacking, recurrent state, allocator overhead, OS memory and scheduling are excluded. In particular, CPU runtime weights need more memory than the GGUF file alone.\n')
    emit(table(['Budget','Unit','Cache','Measured bytes/token','8,192-token conversations'],[[r['budget'],r['unit'],r['cache'],r['bytes_per_token'],r['conversations']] for r in capacities]))
    emit('Real four-slot startup check (`--parallel 4 -c 32768`):\n')
    for i,s in evidence['D-parallel4']:
        if 'n_ctx_slot' in s or 'new slot' in s: emit(f'`logs/D-parallel4.log:{i}`: `{s}`\n')
    emit('## Screenworthy evidence\n')
    emit('### Buffer growth: exact log lines\n')
    for b in blocks:
        if b['block'].startswith('A-'):
            for i,s in evidence[b['block']]:
                if 'KV buffer size' in s or 'RS buffer size' in s: emit(f'`logs/{b["block"]}.log:{i}`: `{s}`\n')
    emit('Formula arithmetic: `results/formulas.jsonl:1` (main) and `:2` (contrast). B’s readable timing extracts: `logs/B-reuse-timing.log:1` and `logs/B-no-reuse-timing.log:1`; lines 2 and 3 contain the other repeats. These extracts are generated from the raw HTTP timing rows: `results/B-r1-reuse.jsonl:1` and `results/B-r1-no-reuse.jsonl:1` through `:64`; repeats 2 and 3 use the same filenames with r2/r3.\n')
    changed=[(i,r) for i,r in enumerate(cs['q4_0-q4_0']['pairs']) if not r['same_text']]
    # Prefer a changed answer over a change confined to continuation text.
    changed.sort(key=lambda item:base[item[0]]['output'].strip().splitlines()[:1]==item[1]['output'].strip().splitlines()[:1])
    if changed:
        i,r=changed[0]; emit(f'q4_0 changed {r["id"]} at generated token {r["first_difference"]}: `results/C-f16-f16.jsonl:{i+1}` versus `results/C-q4_0-q4_0.jsonl:{i+1}`. f16: {base[i]["output"]!r}; q4_0: {r["output"]!r}. Readable answer-line comparison, generated from those raw rows: `logs/C-answer-comparison.log:{i+1}`.\n')
    else: emit('No q4_0 output changed on these checks. There is no changed-output example to show.\n')
    emit('### Exact server command argument arrays\n')
    for b in blocks: emit(f'{b["block"]}:\n\n```json\n{json.dumps(b["command"])}\n```\n')
    emit('## Limits and validation\n')
    loads=[r['loadavg_1m'] for p in D.glob('results/B-*.jsonl') for r in rows(p)]+[r['loadavg_1m'] for p in D.glob('results/C-*.jsonl') for r in rows(p)]
    emit(f'One machine, CPU, one pinned llama.cpp build, one full-attention model and one hybrid contrast. Background work remained active; timed-request one-minute load ranged from {min(loads):.3f} to {max(loads):.3f}, median {med(loads):.3f}. Load is recorded before every timed request and before every server start. No load gate or selective timing rerun was used.\n')
    emit('Raw token prompts and repetitive authored filler do not represent a production chat workload. Greedy output equality is observed, not guaranteed: processing many prompt tokens together can change numerical results relative to single-token decoding. Cache quantization can change output, but unchanged output on a finite check set does not establish general equivalence. No GPU or throughput scaling claim follows.\n')
    emit('C uses one cold full-prompt sample per configuration in fixed order: f16, q8_0, q4_0, then mixed K/V. Its speeds describe these runs, including their background load; this design cannot isolate cache precision from time-varying contention. The later nineteen questions measure retrieval from a reused document prefix, rather than nineteen additional cold prefills.\n')
    emit('Validation checks: formula agrees exactly with every logged KV allocation; complete serial blocks; three 64-token reuse/no-reuse pairs; every B no-reuse prompt fully reevaluated; four cache conditions with twenty 24,576-token tasks and one cold full-prompt evaluation per condition; positive peak RSS and cgroup peak under 48 GB; immutable source hashes in results/summary.json. Initial setup-only pilot logs lacked KV allocation verbosity; preserved separately and excluded from all tables. The separate-document C pilot is also retained and excluded.\n')
    emit('Privacy scan: regenerated by this script over all demo text outputs plus local provenance and pipeline logs. It rejects the actual local account name, home path, host name, private IPv4 ranges and credential patterns. Model publisher identifiers are retained only as necessary provenance. Loopback addresses are local container transport, not LAN addresses. No generated task requests names or organizations. The scan result and scanned-file hashes are saved in `results/privacy.json`.\n')
    (D/'REPORT.md').write_text('\n'.join(out))
    privacy()
    print('Report and summary generated; validation and privacy checks passed.')

def privacy():
    # Build deny values at runtime so the source itself contains no private identity.
    account=pathlib.Path.home().name; host=os.uname().nodename
    forbidden=[str(pathlib.Path.home()),account,host]
    checked=[]
    for p in sorted(WORK.rglob('*')):
        if not p.is_file() or p.suffix not in ['.md','.json','.jsonl','.log','.py','.txt']: continue
        if p.name=='privacy.json': continue
        content=p.read_text(errors='replace')
        for value in forbidden:
            if len(value)>3:
                scanned = content.replace('a desktop processor with 16 cores', '<hardware>') if value == host else content
                assert value.lower() not in scanned.lower(),f'Private identity in {p.name}'
        # llama.cpp's dotted elapsed-time prefix can resemble an IPv4 address.
        address_text=re.sub(r'\b\d+\.\d{2}\.\d{3}\.\d{3}(?=\s+[DIWEF]\s+)','<log-time>',content)
        candidates=re.findall(r'\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b',address_text)
        for candidate in candidates:
            try: ipaddress.IPv4Address(candidate)
            except ipaddress.AddressValueError: continue
            raise AssertionError(f'Private address in {p.name}')
        assert not re.search(r'\b(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,})\b',content),f'Credential pattern in {p.name}'
        checked.append({'file':str(p.relative_to(WORK)),'sha256':sha(p)})
    (D/'results/privacy.json').write_text(json.dumps({'passed':True,'files':checked},indent=2)+'\n')
if __name__=='__main__': main()
