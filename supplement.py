"""Bracket cache/file crossover on actual padded allocation boundaries."""
import math
from run import PROV, server, done

def main():
    for m in PROV['models']:
        f=m['metadata']['fields']; a=f['general.architecture']
        active=f[a+'.block_count']-f.get(a+'.nextn_predict_layers',0)
        layers=sum(i<active for i in f['attention_layer_indices'])
        bpt=2*layers*f[a+'.attention.head_count_kv']*f[a+'.attention.key_length']*2
        cross=m['bytes']/bpt
        lower=math.floor(cross/256)*256
        for c in sorted({lower,lower+256, f[a+'.context_length']}):
            # The contrast job asks for at most 131072, so do not extend it to 262144.
            if c>131072: continue
            block=f'A-{m["role"]}-boundary-{c}'
            if not done(block):
                with server(block,role=m['role'],ctx=c): pass
if __name__=='__main__': main()
