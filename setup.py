"""Pinned publisher download and binary GGUF metadata, no model execution."""
import hashlib, json, pathlib, struct, urllib.request

WORK = pathlib.Path(__file__).resolve().parents[1]
IMAGE = 'ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2'
REPO = 'Qwen/Qwen3-4B-GGUF'
REV = 'bc640142c66e1fdd12af0bd68f40445458f3869b'
FILE = 'Qwen3-4B-Q4_K_M.gguf'

def sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def metadata(path):
    with open(path, 'rb') as f:
        def number(fmt):
            return struct.unpack('<'+fmt, f.read(struct.calcsize('<'+fmt)))[0]
        def string():
            return f.read(number('Q')).decode()
        def value(t):
            if t == 8: return string()
            if t == 9:
                kind, n = number('I'), number('Q')
                return [value(kind) for _ in range(n)]
            return number({0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}[t])
        assert f.read(4) == b'GGUF'
        version, tensors, count = number('I'), number('Q'), number('Q')
        fields = {}
        for _ in range(count):
            key = string(); val = value(number('I'))
            if not key.startswith('tokenizer.'):
                fields[key] = val
        names = []
        for _ in range(tensors):
            name = string(); dims = [number('Q') for _ in range(number('I'))]
            kind, offset = number('I'), number('Q')
            names.append({'name':name, 'dimensions':dims, 'type':kind})
        fields['attention_layer_indices'] = sorted({int(t['name'].split('.')[1]) for t in names if t['name'].endswith('attn_k.weight')})
        return {'version':version, 'fields':fields, 'tensors':names}

def main():
    prov = WORK/'provenance'
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}/revision/{REV}') as r:
        api = json.load(r)
    assert api['sha'] == REV and api['gated'] is False
    (prov/'publisher.json').write_text(json.dumps({'repository':REPO,'revision':REV,'gated':False,'license':api.get('cardData',{}).get('license')}, indent=2)+'\n')
    path = WORK/'models'/FILE
    url = f'https://huggingface.co/{REPO}/resolve/{REV}/{FILE}'
    if not path.exists():
        partial = path.with_suffix('.partial')
        with urllib.request.urlopen(url, timeout=300) as r, partial.open('wb') as out:
            while chunk := r.read(8*1024*1024): out.write(chunk)
        partial.rename(path)
    prior = json.loads((WORK.parent/'specdec/provenance/setup.json').read_text())['models'][1]
    contrast = WORK.parent/'specdec/models/qwen3.5-4b-q4_k_m.gguf'
    assert sha(contrast) == prior['sha256']
    rows = []
    for role, p, repo, rev in [('main',path,REPO,REV),('contrast',contrast,prior['repository'],prior['revision'])]:
        row = {'role':role,'file':str(p.relative_to(WORK.parents[2])), 'repository':repo,'revision':rev,'sha256':sha(p),'bytes':p.stat().st_size,'metadata':metadata(p)}
        rows.append(row)
    (prov/'models.json').write_text(json.dumps({'image':IMAGE,'download_url':url,'models':rows},indent=2)+'\n')
    print('Publisher download and both GGUF hashes recorded.',flush=True)

if __name__ == '__main__': main()
