# KV cache: the memory and reuse measurement


Question: how much memory does cached attention cost, what computation does it save, and what changes when its stored vectors use fewer bits?


## Headline figures


The main model allocates 147,456 bytes of f16 KV cache per token.


At 32,768 tokens, its f16 KV cache is 4.5 GiB.


The main model’s f16 cache already outweighs its GGUF weight file at a measured context of 17,152 tokens.


The hybrid contrast allocates 32,768 bytes of f16 KV cache per token.


Cached generation took a median of 23.413 seconds, including processing the 4,096-token prompt and generating 64 tokens.


Recomputing the growing prompt took a median of 1290.033 seconds for 64 tokens.


The cached and recomputed outputs matched on 3 of the three repeats.


The q8_0-q8_0 cache allocated 2.390625 GiB at 32,768 tokens.


The q8_0-q8_0 cache passed 0 of 20 strict answer-only checks.


The q8_0-q8_0 cache returned the correct code on its first answer line in 20 of 20 authored retrieval checks.


The q4_0-q4_0 cache allocated 1.265625 GiB at 32,768 tokens.


The q4_0-q4_0 cache passed 0 of 20 strict answer-only checks.


The q4_0-q4_0 cache returned the correct code on its first answer line in 20 of 20 authored retrieval checks.


The q8_0-q4_0 cache allocated 1.828125 GiB at 32,768 tokens.


The q8_0-q4_0 cache passed 0 of 20 strict answer-only checks.


The q8_0-q4_0 cache returned the correct code on its first answer line in 20 of 20 authored retrieval checks.


The four-slot server allocated 8,192 context tokens per slot.


## Setup and provenance


Machine: a desktop processor with 16 cores. CPU only; nice 10; eight inference and batch threads; one server at a time. Containers use networking disabled, no exposed ports, and a 44 GiB cgroup limit with no swap. Peak cgroup memory is recorded independently of process peak RSS.


Image: `ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2`.


The publisher GGUF for Qwen3-4B supplies a dense, full-attention GQA model in the requested size range without conversion. Q4_K_M keeps weight memory small enough to observe cache/file crossover within its native context limit. The contrast reuses the previous demo’s verified local Q4_K_M conversion. Publisher names below are necessary model provenance; private identity is excluded.


| Role | Publisher repository | Revision | GGUF bytes | SHA-256 |
| --- | --- | --- | --- | --- |
| main | Qwen/Qwen3-4B-GGUF | bc640142c66e1fdd12af0bd68f40445458f3869b | 2497280256 | 7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5 |
| contrast | Qwen/Qwen3.5-4B | 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a | 2783446464 | 6e1cdfd39c43ec66dc290b75013515ae5b8f738861a4f18234acca3b0602f680 |


Main download: `https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/bc640142c66e1fdd12af0bd68f40445458f3869b/Qwen3-4B-Q4_K_M.gguf`. Gated status and license: `../provenance/publisher.json`. Contrast conversion provenance: `.studio/ai-channel/specdec/provenance/setup.json`; no conversion performed by this job.


Measurement interval: 2026-11-14T12:55:38.040079+00:00 through 2026-11-14T16:42:30.892237+00:00. Seed 12648430; temperature zero; raw token-ID completions. B ignores EOS to measure exactly 64 steps. C permits EOS and caps at 32 generated tokens. Flash attention is on for every condition; server logs confirm effective settings.


## Metadata and formula


| Role | GGUF layers | Runtime layers | KV layers | Attention heads | KV heads | Head size | f16 bytes/token |
| --- | --- | --- | --- | --- | --- | --- | --- |
| main | 36 | 36 | 36 | 32 | 8 | 128 | 147456 |
| contrast | 33 | 32 | 8 | 16 | 4 | 256 | 32768 |


main: 2 × 36 × 8 × 128 × 2 = 147,456 bytes/token. Exact formula evidence: `results/formulas.jsonl:1`. Metadata: `../provenance/models.json`; runtime allocation is confirmed in the logs below.


main file/cache equality by arithmetic: 2,497,280,256 / 147,456 = 16935.765625 tokens. The two boundary runs bracket this value at 256-token allocation boundaries.


contrast: 2 × 8 × 4 × 256 × 2 = 32,768 bytes/token. Exact formula evidence: `results/formulas.jsonl:2`. Metadata: `../provenance/models.json`; runtime allocation is confirmed in the logs below.


contrast file/cache equality by arithmetic: 2,783,446,464 / 32,768 = 84944.044922 tokens. The two boundary runs bracket this value at 256-token allocation boundaries.


The contrast stores 33 blocks in GGUF, including one next-token prediction block. The server uses 32 runtime layers: eight full-attention layers and 24 recurrent layers. Its separate recurrent-state allocation is 50.25 MiB for one slot and does not grow with context in this sweep. Counting every GGUF block as a KV layer gives the wrong prediction.


q8_0 stores 32 values plus a two-byte scale in 34 bytes; q4_0 uses 18 bytes per block of 32 values. Replace bytes/element by 34/32 and 18/32, respectively. These include block-scale overhead. All measured allocations below exactly equal the corresponding formula.


## A. Growth and every server run


The main model’s GGUF native limit is 40,960 tokens. The requested 65,536 and 131,072 main-model contexts are skipped. A supplementary 40,960-token run reaches its native limit. Contrast runs cover every requested size through 131,072.


A and D peaks cover startup allocation only. They do not measure filling the entire context. Peak RSS is the server process kernel VmHWM; cgroup peak includes helper processes and file-cache charges, and can be smaller than process RSS because mapped pages can be counted more than once in RSS.


| Block | Context | K/V | KV MiB | Formula bytes | Peak RSS KiB | Cgroup peak bytes | Load at server start | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A-main-4096 | 4096 | f16/f16 | 576.0 | 603979776 | 4826764 | 2467184640 | 3.42431640625 | logs/A-main-4096.log:270 |
| A-main-16384 | 16384 | f16/f16 | 2304.0 | 2415919104 | 6578796 | 4265496576 | 3.42431640625 | logs/A-main-16384.log:270 |
| A-main-32768 | 32768 | f16/f16 | 4608.0 | 4831838208 | 8938164 | 6685122560 | 3.42431640625 | logs/A-main-32768.log:270 |
| A-contrast-4096 | 4096 | f16/f16 | 128.0 | 134217728 | 4573484 | 1996931072 | 3.39013671875 | logs/A-contrast-4096.log:286 |
| A-contrast-16384 | 16384 | f16/f16 | 512.0 | 536870912 | 4965800 | 2395938816 | 3.39013671875 | logs/A-contrast-16384.log:286 |
| A-contrast-32768 | 32768 | f16/f16 | 1024.0 | 1073741824 | 5491008 | 2936111104 | 3.39013671875 | logs/A-contrast-32768.log:286 |
| A-contrast-65536 | 65536 | f16/f16 | 2048.0 | 2147483648 | 6517520 | 3987091456 | 3.27880859375 | logs/A-contrast-65536.log:286 |
| A-contrast-131072 | 131072 | f16/f16 | 4096.0 | 4294967296 | 8614840 | 6135459840 | 3.27880859375 | logs/A-contrast-131072.log:286 |
| D-parallel4 | 32768 | f16/f16 | 4608.0 | 4831838208 | 8939412 | 6686797824 | 3.09619140625 | logs/D-parallel4.log:270 |
| B-r1 | 8192 | f16/f16 | 1152.0 | 1207959552 | 5492688 | 3154849792 | 3.09619140625 | logs/B-r1.log:270 |
| B-r2 | 8192 | f16/f16 | 1152.0 | 1207959552 | 5496368 | 3158147072 | 9.44140625 | logs/B-r2.log:270 |
| B-r3 | 8192 | f16/f16 | 1152.0 | 1207959552 | 5496404 | 3158855680 | 10.2353515625 | logs/B-r3.log:270 |
| C-f16-f16 | 32768 | f16/f16 | 4608.0 | 4831838208 | 9056496 | 6811463680 | 5.93505859375 | logs/C-f16-f16.log:270 |
| C-q8_0-q8_0 | 32768 | q8_0/q8_0 | 2448.0 | 2566914048 | 6849280 | 4547706880 | 12.04443359375 | logs/C-q8_0-q8_0.log:270 |
| C-q4_0-q4_0 | 32768 | q4_0/q4_0 | 1296.0 | 1358954496 | 5671612 | 3338747904 | 9.90576171875 | logs/C-q4_0-q4_0.log:270 |
| C-q8_0-q4_0 | 32768 | q8_0/q4_0 | 1872.0 | 1962934272 | 6263212 | 3946967040 | 10.099609375 | logs/C-q8_0-q4_0.log:270 |
| A-main-boundary-16896 | 16896 | f16/f16 | 2376.0 | 2491416576 | 6669968 | 4383862784 | 9.3212890625 | logs/A-main-boundary-16896.log:270 |
| A-main-boundary-17152 | 17152 | f16/f16 | 2412.0 | 2529165312 | 6706588 | 4398780416 | 9.3212890625 | logs/A-main-boundary-17152.log:270 |
| A-main-boundary-40960 | 40960 | f16/f16 | 5760.0 | 6039797760 | 10117944 | 7895678976 | 8.89501953125 | logs/A-main-boundary-40960.log:269 |
| A-contrast-boundary-84736 | 84736 | f16/f16 | 2648.0 | 2776629248 | 7154836 | 4642787328 | 8.89501953125 | logs/A-contrast-boundary-84736.log:286 |
| A-contrast-boundary-84992 | 84992 | f16/f16 | 2656.0 | 2785017856 | 7170176 | 4661321728 | 8.89501953125 | logs/A-contrast-boundary-84992.log:286 |


## B. What cache reuse saves


Both paths start with exactly 4,096 identical token IDs. Normal decoding processes that prompt once and generates 64 steps. No-reuse sends the original prompt plus its own generated token IDs afresh on each of 64 requests, with cache_prompt=false and n_predict=1. Server prompt_n is checked at every step: 4,096 through 4,159. No prompt text is retokenized between steps.


Times below are measured inside the container-side HTTP client. Total no-reuse time sums HTTP request durations and excludes Python/docker launch gaps; normal time is one HTTP request. First and 64th latency are individual step latency for no-reuse. Normal token 64 is cumulative arrival time; its incremental latency is reported separately below. Timing does not include server startup. Order alternates across repeats.


| Repeat | Reuse total s | No reuse total s | Reuse token1 s | Reuse token64 cumulative s | No reuse token1 s | No reuse token64 step s | Exact text | Exact IDs | First differing token |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 22.969991527032107 | 1258.4978655177983 | 18.70314887101995 | 22.96972581499722 | 18.530030113004614 | 20.87137927598087 | True | True | None |
| 2 | 23.714059752994217 | 1314.2935688528232 | 19.319877375965007 | 23.713789622008335 | 19.271415842988063 | 20.292175679991487 | True | True | None |
| 3 | 23.41271154396236 | 1290.0331810231437 | 19.088539967953693 | 23.412445082969498 | 19.75910261098761 | 22.41308927902719 | True | True | None |


Repeat 1: normal token 64 incremental arrival latency 0.068862 s. Evidence: `results/B-r1-reuse.jsonl:1`; no-reuse: `results/B-r1-no-reuse.jsonl:1` and `:64`.


Repeat 2: normal token 64 incremental arrival latency 0.067217 s. Evidence: `results/B-r2-reuse.jsonl:1`; no-reuse: `results/B-r2-no-reuse.jsonl:1` and `:64`.


Repeat 3: normal token 64 incremental arrival latency 0.067784 s. Evidence: `results/B-r3-reuse.jsonl:1`; no-reuse: `results/B-r3-no-reuse.jsonl:1` and `:64`.


| Mode | Median total s | Median token1 s | Median token64 (cumulative reuse / step no-reuse) s |
| --- | --- | --- | --- |
| reuse | 23.41271154396236 | 19.088539967953693 | 23.412445082969498 |
| no-reuse | 1290.0331810231437 | 19.271415842988063 | 20.87137927598087 |


Normal token 64 median incremental arrival latency: 0.067784 s. No-reuse token 64 median cumulative time: 1290.033181 s.


## C. Quantized cache: authored retrieval checks


One fixed self-written ledger contains twenty unique vault/code assignments at varied depths, surrounded by neutral filler. Twenty questions each have one checkable answer; every document-plus-question prompt is exactly 24,576 tokens. These are authored checks, not a benchmark. Each fresh cache configuration processes the first question cold; its speed below measures the entire prompt. Subsequent questions reuse the common document prefix, with evaluated and reused token counts shown explicitly. Generation speed is the median over twenty questions. This C protocol measures stored-cache retrieval, while B separately forces full recomputation.


Strict answer-only correctness strips surrounding whitespace only. First-line correctness checks only the first nonempty answer line, preserving the strict score separately. This secondary score and the shared-document protocol were fixed after observing continuation text in three exploratory f16 outputs, before any quantized-cache output was measured; see fixtures/scoring-policy.json and ../pilot-separate-documents/protocol-change.json. Those exploratory rows remain retained and excluded. Raw completion can retrieve a code and still fail the requested answer-only format. f16 output exact-match compares unmodified text. First difference is one-based emitted token ID, including terminal tokens. An ended sequence differs at its next token.


| K/V | Strict answer-only /20 | First answer line /20 | Exact f16 text /20 | Cold prompt tokens/s (one run) | Median generation tokens/s |
| --- | --- | --- | --- | --- | --- |
| f16-f16 | 0 | 19 | 20 | 74.75619165130723 | 4.075011171586192 |
| q8_0-q8_0 | 0 | 20 | 12 | 8.913527596877707 | 2.272339752136586 |
| q4_0-q4_0 | 0 | 20 | 1 | 12.299390902543223 | 3.9309028866927602 |
| q8_0-q4_0 | 0 | 20 | 12 | 11.006070837789395 | 2.6480480100732517 |


| Condition | Task | Depth fraction | Expected | Output | Strict | First line | Same f16 | First token difference | Evaluated prompt tokens | Reused tokens | Prompt tok/s | Generation tok/s | Load | At limit | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| f16-f16 | T01 | 0.025309244791666668 | 419 | " 419\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-01" | False | True | True | None | 24576 | 0 | 74.75619165130723 | 4.051459812851308 | 5.69970703125 | True | results/C-f16-f16.jsonl:1 |
| f16-f16 | T02 | 0.0751953125 | 556 | ' 556\nThe access code for vault-02 is 556. This is the only assigned code for that vault.\nAnswer: ' | False | True | True | None | 9 | 24567 | 5.54909531249422 | 4.03994383696142 | 12.39990234375 | True | results/C-f16-f16.jsonl:2 |
| f16-f16 | T03 | 0.1251220703125 | 693 | " 693\nOkay, let's see. The user is asking for the access code of vault-03. I need to look through the provided" | False | True | True | None | 9 | 24567 | 6.116291081088428 | 4.103134265141889 | 12.5283203125 | True | results/C-f16-f16.jsonl:3 |
| f16-f16 | T04 | 0.175048828125 | 830 | " 830\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-04" | False | True | True | None | 9 | 24567 | 6.018750413789091 | 4.032377651158229 | 12.2255859375 | True | results/C-f16-f16.jsonl:4 |
| f16-f16 | T05 | 0.22493489583333334 | 967 | " 967\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-05" | False | True | True | None | 9 | 24567 | 6.118465733532659 | 4.033312559605204 | 12.33837890625 | True | results/C-f16-f16.jsonl:5 |
| f16-f16 | T06 | 0.2748616536458333 | 104 | " 104\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-06" | False | True | True | None | 9 | 24567 | 6.133188317502893 | 4.112054274871728 | 12.88916015625 | True | results/C-f16-f16.jsonl:6 |
| f16-f16 | T07 | 0.3247477213541667 | 241 | ' 241\nThe access code for vault-07 is 241. This is the only assigned code for that vault.\nThe access code' | False | True | True | None | 9 | 24567 | 6.058456022677474 | 3.981934349206137 | 12.52490234375 | True | results/C-f16-f16.jsonl:7 |
| f16-f16 | T08 | 0.3746744791666667 | 378 | " 378\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-08" | False | True | True | None | 9 | 24567 | 5.790067589388993 | 4.073466412166997 | 12.142578125 | True | results/C-f16-f16.jsonl:8 |
| f16-f16 | T09 | 0.4246012369791667 | 515 | ' 515\nThe access code for vault-09 is 515. This is the only assigned code for that vault.\nThe access code' | False | True | True | None | 9 | 24567 | 5.945263936689545 | 4.113122545975091 | 12.29150390625 | True | results/C-f16-f16.jsonl:9 |
| f16-f16 | T10 | 0.4744873046875 | 652 | ' 652\nThe access code for vault-10 is 652. This is the only assigned code for that vault.\nAnswer: ' | False | True | True | None | 10 | 24566 | 6.012921768881326 | 4.098701491702576 | 12.15380859375 | True | results/C-f16-f16.jsonl:10 |
| f16-f16 | T11 | 0.5244140625 | 789 | ' 063\n\nThe access code for vault-11 is 063. This is the only assigned code for that vault.\nThe answer is' | False | False | True | None | 9 | 24567 | 6.313428030077172 | 4.085048603512957 | 12.197265625 | True | results/C-f16-f16.jsonl:11 |
| f16-f16 | T12 | 0.5743001302083334 | 926 | " 926\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-12" | False | True | True | None | 9 | 24567 | 5.946764563626417 | 4.096622136824537 | 12.1796875 | True | results/C-f16-f16.jsonl:12 |
| f16-f16 | T13 | 0.6242268880208334 | 063 | ' 063\nThe access code for vault-13 is 063. This is the only assigned code for that vault.\nAnswer: ' | False | True | True | None | 9 | 24567 | 6.179090643826917 | 4.082195399418458 | 12.2802734375 | True | results/C-f16-f16.jsonl:13 |
| f16-f16 | T14 | 0.6741536458333334 | 200 | ' 200\nThe access code for vault-14 is 200. This is the only assigned code for that vault.\nThe access code' | False | True | True | None | 9 | 24567 | 6.051156476855335 | 4.123037832995156 | 12.07080078125 | True | results/C-f16-f16.jsonl:14 |
| f16-f16 | T15 | 0.7240397135416666 | 337 | ' 337\nThe access code for vault-15 is 337. This is the only assigned code for that vault.\nAnswer: ' | False | True | True | None | 9 | 24567 | 6.203555188550168 | 3.964641029251505 | 11.82470703125 | True | results/C-f16-f16.jsonl:15 |
| f16-f16 | T16 | 0.7739664713541666 | 474 | " 474\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-16" | False | True | True | None | 9 | 24567 | 6.6374226740258475 | 4.069720348509845 | 11.9443359375 | True | results/C-f16-f16.jsonl:16 |
| f16-f16 | T17 | 0.8238525390625 | 611 | ' 611\nThe access code for vault-17 is 611. This is the only assigned code for that vault.\nThe access code' | False | True | True | None | 9 | 24567 | 5.920589111773487 | 4.0740858047153985 | 11.55859375 | True | results/C-f16-f16.jsonl:17 |
| f16-f16 | T18 | 0.873779296875 | 748 | " 748\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-18" | False | True | True | None | 9 | 24567 | 6.0135384796304745 | 4.075936538456987 | 11.318359375 | True | results/C-f16-f16.jsonl:18 |
| f16-f16 | T19 | 0.9237060546875 | 885 | " 885\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-19" | False | True | True | None | 9 | 24567 | 5.9012639851760245 | 4.06663669599149 | 11.6376953125 | True | results/C-f16-f16.jsonl:19 |
| f16-f16 | T20 | 0.9735921223958334 | 022 | ' 022\nThe access code for vault-20 is 022. This is the only assigned code for that vault.\nThe storage room' | False | True | True | None | 10 | 24566 | 6.234958163430724 | 4.113958235626825 | 11.69970703125 | True | results/C-f16-f16.jsonl:20 |
| q8_0-q8_0 | T01 | 0.025309244791666668 | 419 | " 419\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-01" | False | True | True | None | 24576 | 0 | 8.913527596877707 | 2.2653241138052067 | 11.31982421875 | True | results/C-q8_0-q8_0.jsonl:1 |
| q8_0-q8_0 | T02 | 0.0751953125 | 556 | " 556\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-02" | False | True | False | 6 | 9 | 24567 | 2.87110096513654 | 2.246231132111359 | 10.1767578125 | True | results/C-q8_0-q8_0.jsonl:2 |
| q8_0-q8_0 | T03 | 0.1251220703125 | 693 | " 693\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-03" | False | True | False | 14 | 9 | 24567 | 2.7625793282327935 | 2.270325122275317 | 10.291015625 | True | results/C-q8_0-q8_0.jsonl:3 |
| q8_0-q8_0 | T04 | 0.175048828125 | 830 | " 830\nOkay, let's see. The user is asking for the access code for vault-04. I need to look through the provided" | False | True | False | 14 | 9 | 24567 | 2.808947559133808 | 2.2719707264633726 | 10.4853515625 | True | results/C-q8_0-q8_0.jsonl:4 |
| q8_0-q8_0 | T05 | 0.22493489583333334 | 967 | ' 967\nAnswer: 967\nAnswer: 967\nAnswer: 967\nAnswer: 967' | False | True | False | 6 | 9 | 24567 | 2.7395750797292444 | 2.243578354042888 | 10.38330078125 | True | results/C-q8_0-q8_0.jsonl:5 |
| q8_0-q8_0 | T06 | 0.2748616536458333 | 104 | " 104\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-06" | False | True | True | None | 9 | 24567 | 2.784680174840786 | 2.2478408401065852 | 10.36572265625 | True | results/C-q8_0-q8_0.jsonl:6 |
| q8_0-q8_0 | T07 | 0.3247477213541667 | 241 | ' 241\nThe access code for vault-07 is 241. This is the only assigned code for that vault.\nThe access code' | False | True | True | None | 9 | 24567 | 2.8068056929504266 | 2.3008996294883595 | 10.107421875 | True | results/C-q8_0-q8_0.jsonl:7 |
| q8_0-q8_0 | T08 | 0.3746744791666667 | 378 | " 378\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-08" | False | True | True | None | 9 | 24567 | 2.873299006987863 | 2.2823561719880536 | 9.72021484375 | True | results/C-q8_0-q8_0.jsonl:8 |
| q8_0-q8_0 | T09 | 0.4246012369791667 | 515 | ' 515\nThe access code for vault-09 is 515. This is the only assigned code for that vault.\nThe access code' | False | True | True | None | 9 | 24567 | 2.817763935251542 | 2.104733293968031 | 9.521484375 | True | results/C-q8_0-q8_0.jsonl:9 |
| q8_0-q8_0 | T10 | 0.4744873046875 | 652 | " 652\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-10" | False | True | False | 6 | 10 | 24566 | 2.7739512661145764 | 2.263486307769738 | 9.6953125 | True | results/C-q8_0-q8_0.jsonl:10 |
| q8_0-q8_0 | T11 | 0.5244140625 | 789 | ' 789\nAnswer: 789\nAnswer: 789\nAnswer: 789\nAnswer: 789' | False | True | False | 2 | 9 | 24567 | 2.8519495927415983 | 2.2993585308908804 | 10.30615234375 | True | results/C-q8_0-q8_0.jsonl:11 |
| q8_0-q8_0 | T12 | 0.5743001302083334 | 926 | " 926\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-12" | False | True | True | None | 9 | 24567 | 2.809985940703677 | 2.236174347156113 | 10.01611328125 | True | results/C-q8_0-q8_0.jsonl:12 |
| q8_0-q8_0 | T13 | 0.6242268880208334 | 063 | ' 063\nThe access code for vault-13 is 063. This is the only assigned code for that vault.\nAnswer: ' | False | True | True | None | 9 | 24567 | 2.8246734599017205 | 2.2702060790553134 | 10.0986328125 | True | results/C-q8_0-q8_0.jsonl:13 |
| q8_0-q8_0 | T14 | 0.6741536458333334 | 200 | ' 200\nThe access code for vault-14 is 200. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 30 | 9 | 24567 | 2.805225699108998 | 2.2807726816405522 | 9.7744140625 | True | results/C-q8_0-q8_0.jsonl:14 |
| q8_0-q8_0 | T15 | 0.7240397135416666 | 337 | ' 337\nThe access code for vault-15 is 337. This is the only assigned code for that vault.\nAnswer: ' | False | True | True | None | 9 | 24567 | 2.8078906719687957 | 2.29854716989526 | 10.01513671875 | True | results/C-q8_0-q8_0.jsonl:15 |
| q8_0-q8_0 | T16 | 0.7739664713541666 | 474 | ' 474\nThe access code for vault-16 is 474. This is the only assigned code for that vault.\nThe storage room' | False | True | False | 6 | 9 | 24567 | 2.851750784865188 | 2.3247711262826174 | 10.435546875 | True | results/C-q8_0-q8_0.jsonl:16 |
| q8_0-q8_0 | T17 | 0.8238525390625 | 611 | ' 611\nThe access code for vault-17 is 611. This is the only assigned code for that vault.\nThe access code' | False | True | True | None | 9 | 24567 | 2.640095184231709 | 2.2815077321768986 | 10.41845703125 | True | results/C-q8_0-q8_0.jsonl:17 |
| q8_0-q8_0 | T18 | 0.873779296875 | 748 | " 748\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-18" | False | True | True | None | 9 | 24567 | 2.8209566992549853 | 2.327048675477674 | 10.375 | True | results/C-q8_0-q8_0.jsonl:18 |
| q8_0-q8_0 | T19 | 0.9237060546875 | 885 | " 885\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-19" | False | True | True | None | 9 | 24567 | 2.816606965030886 | 2.2727087778097994 | 10.2255859375 | True | results/C-q8_0-q8_0.jsonl:19 |
| q8_0-q8_0 | T20 | 0.9735921223958334 | 022 | ' 022\nThe access code for vault-20 is 022. This is the only assigned code for that vault.\nThe storage room' | False | True | True | None | 10 | 24566 | 2.808079293419856 | 2.324527597878921 | 10.27490234375 | True | results/C-q8_0-q8_0.jsonl:20 |
| q4_0-q4_0 | T01 | 0.025309244791666668 | 419 | ' 419\nThe access code for vault-01 is 419. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 6 | 24576 | 0 | 12.299390902543223 | 3.8982006283144925 | 9.2724609375 | True | results/C-q4_0-q4_0.jsonl:1 |
| q4_0-q4_0 | T02 | 0.0751953125 | 556 | ' 556\nThe access code for vault-02 is 556. This is the only assigned code for that vault.\nAnswer: ' | False | True | True | None | 9 | 24567 | 5.8078342521542226 | 3.8250666240233433 | 10.505859375 | True | results/C-q4_0-q4_0.jsonl:2 |
| q4_0-q4_0 | T03 | 0.1251220703125 | 693 | ' 693\nThe access code for vault-03 is 693. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 6 | 9 | 24567 | 5.041409578118042 | 3.929139614751663 | 10.35400390625 | True | results/C-q4_0-q4_0.jsonl:3 |
| q4_0-q4_0 | T04 | 0.175048828125 | 830 | " 830\nOkay, let's see. The user is asking for the access code for vault-04. I need to look through the provided" | False | True | False | 14 | 9 | 24567 | 5.464467602993071 | 3.964104648782247 | 10.22509765625 | True | results/C-q4_0-q4_0.jsonl:4 |
| q4_0-q4_0 | T05 | 0.22493489583333334 | 967 | ' 967\n\nThe access code for vault-05 is 967. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 5 | 9 | 24567 | 5.4796055171103735 | 3.9239264580234803 | 10.197265625 | True | results/C-q4_0-q4_0.jsonl:5 |
| q4_0-q4_0 | T06 | 0.2748616536458333 | 104 | ' 104\nAnswer: 104\nAnswer: 104\nAnswer: 104\nAnswer: 104' | False | True | False | 6 | 9 | 24567 | 5.6920775766928395 | 4.01370356080243 | 10.3212890625 | True | results/C-q4_0-q4_0.jsonl:6 |
| q4_0-q4_0 | T07 | 0.3247477213541667 | 241 | ' 241\n\nThe access code for vault-07 is 241. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 5 | 9 | 24567 | 5.114970324647167 | 3.9908056986130664 | 10.29541015625 | True | results/C-q4_0-q4_0.jsonl:7 |
| q4_0-q4_0 | T08 | 0.3746744791666667 | 378 | ' 378\nThe access code for vault-08 is 378. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 6 | 9 | 24567 | 5.081771347392149 | 3.928796021726496 | 10.685546875 | True | results/C-q4_0-q4_0.jsonl:8 |
| q4_0-q4_0 | T09 | 0.4246012369791667 | 515 | ' 515\nThe access code for vault-09 is 515. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 30 | 9 | 24567 | 5.182373480988751 | 3.9026827040907923 | 11.16943359375 | True | results/C-q4_0-q4_0.jsonl:9 |
| q4_0-q4_0 | T10 | 0.4744873046875 | 652 | ' 652\nAnswer: 652\nAnswer: 652\nAnswer: 652\nAnswer: 652' | False | True | False | 6 | 10 | 24566 | 5.4361741511006345 | 3.995921066895457 | 11.06298828125 | True | results/C-q4_0-q4_0.jsonl:10 |
| q4_0-q4_0 | T11 | 0.5244140625 | 789 | ' 789\n\nQuestion: What is the access code for vault-12? Return only the code.\nAnswer: 926\n\nQuestion:' | False | True | False | 2 | 9 | 24567 | 5.214253683870227 | 3.8864129373922696 | 10.97265625 | True | results/C-q4_0-q4_0.jsonl:11 |
| q4_0-q4_0 | T12 | 0.5743001302083334 | 926 | ' 926\n\nThe access code for vault-12 is 926. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 5 | 9 | 24567 | 5.198135602030738 | 3.8342296772840196 | 10.94189453125 | True | results/C-q4_0-q4_0.jsonl:12 |
| q4_0-q4_0 | T13 | 0.6242268880208334 | 063 | ' 063\n\nThe access code for vault-13 is 063. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 5 | 9 | 24567 | 5.726392945083892 | 3.952740524260901 | 11.39990234375 | True | results/C-q4_0-q4_0.jsonl:13 |
| q4_0-q4_0 | T14 | 0.6741536458333334 | 200 | ' 200\n\nThe access code for vault-14 is 200. This is the only assigned code for that vault.\nThe storage room' | False | True | False | 5 | 9 | 24567 | 5.306872872091392 | 3.928250380089904 | 11.41845703125 | True | results/C-q4_0-q4_0.jsonl:14 |
| q4_0-q4_0 | T15 | 0.7240397135416666 | 337 | ' 337\n\nThe access code for vault-15 is 337. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 5 | 9 | 24567 | 5.550765450555632 | 4.057825319782815 | 11.2802734375 | True | results/C-q4_0-q4_0.jsonl:15 |
| q4_0-q4_0 | T16 | 0.7739664713541666 | 474 | ' 474\n\nThe access code for vault-16 is 474. This is the only assigned code for that vault.\nThe storage room' | False | True | False | 5 | 9 | 24567 | 5.7431399788269575 | 3.9326661586338574 | 10.92919921875 | True | results/C-q4_0-q4_0.jsonl:16 |
| q4_0-q4_0 | T17 | 0.8238525390625 | 611 | ' 611\n\nThe access code for vault-17 is 611. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 5 | 9 | 24567 | 5.392948180958578 | 3.9748466574681025 | 10.78564453125 | True | results/C-q4_0-q4_0.jsonl:17 |
| q4_0-q4_0 | T18 | 0.873779296875 | 748 | ' 748\n\nThe access code for vault-18 is 748. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 5 | 9 | 24567 | 5.4299756375093065 | 4.0639945421864265 | 10.8125 | True | results/C-q4_0-q4_0.jsonl:18 |
| q4_0-q4_0 | T19 | 0.9237060546875 | 885 | ' 885\n\nThe access code for vault-19 is 885. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 5 | 9 | 24567 | 5.240641524397807 | 3.7985038306073142 | 10.98779296875 | True | results/C-q4_0-q4_0.jsonl:19 |
| q4_0-q4_0 | T20 | 0.9735921223958334 | 022 | ' 022\n\nThe access code for vault-20 is 022. This is the only assigned code for that vault.\nAnswer: ' | False | True | False | 5 | 10 | 24566 | 5.416217346302647 | 3.9518697953237396 | 10.90966796875 | True | results/C-q4_0-q4_0.jsonl:20 |
| q8_0-q4_0 | T01 | 0.025309244791666668 | 419 | " 419\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-01" | False | True | True | None | 24576 | 0 | 11.006070837789395 | 2.65038407485095 | 9.61083984375 | True | results/C-q8_0-q4_0.jsonl:1 |
| q8_0-q4_0 | T02 | 0.0751953125 | 556 | ' 556\nThe access code for vault-02 is 556. This is the only assigned code for that vault.\nAnswer: ' | False | True | True | None | 9 | 24567 | 3.818277159405435 | 2.6598905240542052 | 9.52197265625 | True | results/C-q8_0-q4_0.jsonl:2 |
| q8_0-q4_0 | T03 | 0.1251220703125 | 693 | " 693\nOkay, let's see. The user is asking for the access code of vault-03. I need to look through the provided" | False | True | True | None | 9 | 24567 | 4.044502106062125 | 2.5732299747093 | 10.16259765625 | True | results/C-q8_0-q4_0.jsonl:3 |
| q8_0-q4_0 | T04 | 0.175048828125 | 830 | " 830\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-04" | False | True | True | None | 9 | 24567 | 3.9562213338795846 | 2.6199092311318575 | 9.904296875 | True | results/C-q8_0-q4_0.jsonl:4 |
| q8_0-q4_0 | T05 | 0.22493489583333334 | 967 | ' 967\nAnswer: 967\nAnswer: 967\nAnswer: 967\nAnswer: 967' | False | True | False | 6 | 9 | 24567 | 3.9125127374025785 | 2.683491756010351 | 9.703125 | True | results/C-q8_0-q4_0.jsonl:5 |
| q8_0-q4_0 | T06 | 0.2748616536458333 | 104 | ' 104\nAnswer: 104\nAnswer: 104\nAnswer: 104\nAnswer: 104' | False | True | False | 6 | 9 | 24567 | 3.882732839938653 | 2.388579875998802 | 9.54638671875 | True | results/C-q8_0-q4_0.jsonl:6 |
| q8_0-q4_0 | T07 | 0.3247477213541667 | 241 | " 241\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-07" | False | True | False | 6 | 9 | 24567 | 3.4419695408642097 | 2.2312783331861414 | 10.28076171875 | True | results/C-q8_0-q4_0.jsonl:7 |
| q8_0-q4_0 | T08 | 0.3746744791666667 | 378 | " 378\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-08" | False | True | True | None | 9 | 24567 | 3.3628680332116847 | 2.26850476045724 | 10.8837890625 | True | results/C-q8_0-q4_0.jsonl:8 |
| q8_0-q4_0 | T09 | 0.4246012369791667 | 515 | ' 515\nThe access code for vault-09 is 515. This is the only assigned code for that vault.\nThe access code' | False | True | True | None | 9 | 24567 | 3.371906697093754 | 2.2486585482355754 | 13.1708984375 | True | results/C-q8_0-q4_0.jsonl:9 |
| q8_0-q4_0 | T10 | 0.4744873046875 | 652 | " 652\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-10" | False | True | False | 6 | 10 | 24566 | 3.4382905919429847 | 2.3494573814494117 | 13.34814453125 | True | results/C-q8_0-q4_0.jsonl:10 |
| q8_0-q4_0 | T11 | 0.5244140625 | 789 | ' 789\nAnswer: 789\nAnswer: 789\nAnswer: 789\nAnswer: 789' | False | True | False | 2 | 9 | 24567 | 3.9226146580264545 | 2.5859619636694036 | 13.27685546875 | True | results/C-q8_0-q4_0.jsonl:11 |
| q8_0-q4_0 | T12 | 0.5743001302083334 | 926 | " 926\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-12" | False | True | True | None | 9 | 24567 | 3.994549658909843 | 2.538038441785217 | 12.4765625 | True | results/C-q8_0-q4_0.jsonl:12 |
| q8_0-q4_0 | T13 | 0.6242268880208334 | 063 | ' 063\nThe access code for vault-13 is 063. This is the only assigned code for that vault.\nAnswer: ' | False | True | True | None | 9 | 24567 | 4.054985604801104 | 2.645711945295553 | 12.068359375 | True | results/C-q8_0-q4_0.jsonl:13 |
| q8_0-q4_0 | T14 | 0.6741536458333334 | 200 | " 200\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-14" | False | True | False | 6 | 9 | 24567 | 4.060866065417845 | 2.676192761848196 | 11.4560546875 | True | results/C-q8_0-q4_0.jsonl:14 |
| q8_0-q4_0 | T15 | 0.7240397135416666 | 337 | ' 337\nThe access code for vault-15 is 337. This is the only assigned code for that vault.\nAnswer: ' | False | True | True | None | 9 | 24567 | 4.0347599048872596 | 2.694835755845794 | 11.31201171875 | True | results/C-q8_0-q4_0.jsonl:15 |
| q8_0-q4_0 | T16 | 0.7739664713541666 | 474 | " 474\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-16" | False | True | True | None | 9 | 24567 | 3.949739997393172 | 2.695603184255173 | 10.873046875 | True | results/C-q8_0-q4_0.jsonl:16 |
| q8_0-q4_0 | T17 | 0.8238525390625 | 611 | " 611\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-17" | False | True | False | 6 | 9 | 24567 | 3.9960252868480155 | 2.683294784774224 | 10.76611328125 | True | results/C-q8_0-q4_0.jsonl:17 |
| q8_0-q4_0 | T18 | 0.873779296875 | 748 | " 748\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-18" | False | True | True | None | 9 | 24567 | 4.0154568318313295 | 2.6837017666289302 | 10.3740234375 | True | results/C-q8_0-q4_0.jsonl:18 |
| q8_0-q4_0 | T19 | 0.9237060546875 | 885 | " 885\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-19" | False | True | True | None | 9 | 24567 | 4.042302243837061 | 2.715368583255566 | 10.14892578125 | True | results/C-q8_0-q4_0.jsonl:19 |
| q8_0-q4_0 | T20 | 0.9735921223958334 | 022 | " 022\nOkay, let's see. The user provided a storage ledger with multiple entries, and they want the access code for vault-20" | False | True | False | 6 | 10 | 24566 | 3.966520976351205 | 2.717332231908002 | 9.9716796875 | True | results/C-q8_0-q4_0.jsonl:20 |


## D. Conversations that fit: arithmetic, not a serving benchmark


floor((budget − GGUF file bytes) / (8,192 × measured cache bytes/token)). GB means decimal 10^9 bytes. GiB figures are included to avoid unit ambiguity. These are upper bounds: compute buffers, weight repacking, recurrent state, allocator overhead, OS memory and scheduling are excluded. In particular, CPU runtime weights need more memory than the GGUF file alone.


| Budget | Unit | Cache | Measured bytes/token | 8,192-token conversations |
| --- | --- | --- | --- | --- |
| 16 | GB | f16 | 147456 | 11 |
| 16 | GB | q8_0 | 78336.0 | 21 |
| 64 | GB | f16 | 147456 | 50 |
| 64 | GB | q8_0 | 78336.0 | 95 |
| 16 | GiB | f16 | 147456 | 12 |
| 16 | GiB | q8_0 | 78336.0 | 22 |
| 64 | GiB | f16 | 147456 | 54 |
| 64 | GiB | q8_0 | 78336.0 | 103 |


Real four-slot startup check (`--parallel 4 -c 32768`):


`logs/D-parallel4.log:283`: `0.01.370.334 I srv    load_model: initializing, n_slots = 4, n_ctx_slot = 8192, kv_unified = 'false'`


`logs/D-parallel4.log:285`: `0.01.370.365 I slot   load_model: id  0 | task -1 | new slot, n_ctx = 8192`


`logs/D-parallel4.log:286`: `0.01.370.374 I slot   load_model: id  1 | task -1 | new slot, n_ctx = 8192`


`logs/D-parallel4.log:287`: `0.01.370.374 I slot   load_model: id  2 | task -1 | new slot, n_ctx = 8192`


`logs/D-parallel4.log:288`: `0.01.370.374 I slot   load_model: id  3 | task -1 | new slot, n_ctx = 8192`


## Screenworthy evidence


### Buffer growth: exact log lines


`logs/A-main-4096.log:270`: `0.00.467.659 I llama_kv_cache:        CPU KV buffer size =   576.00 MiB`


`logs/A-main-16384.log:270`: `0.00.653.326 I llama_kv_cache:        CPU KV buffer size =  2304.00 MiB`


`logs/A-main-32768.log:270`: `0.01.019.516 I llama_kv_cache:        CPU KV buffer size =  4608.00 MiB`


`logs/A-contrast-4096.log:286`: `0.00.578.106 I llama_kv_cache:        CPU KV buffer size =   128.00 MiB`


`logs/A-contrast-4096.log:290`: `0.00.580.411 I llama_memory_recurrent:        CPU RS buffer size =    50.25 MiB`


`logs/A-contrast-16384.log:286`: `0.00.600.959 I llama_kv_cache:        CPU KV buffer size =   512.00 MiB`


`logs/A-contrast-16384.log:290`: `0.00.603.012 I llama_memory_recurrent:        CPU RS buffer size =    50.25 MiB`


`logs/A-contrast-32768.log:286`: `0.00.616.585 I llama_kv_cache:        CPU KV buffer size =  1024.00 MiB`


`logs/A-contrast-32768.log:290`: `0.00.618.689 I llama_memory_recurrent:        CPU RS buffer size =    50.25 MiB`


`logs/A-contrast-65536.log:286`: `0.00.696.478 I llama_kv_cache:        CPU KV buffer size =  2048.00 MiB`


`logs/A-contrast-65536.log:290`: `0.00.705.529 I llama_memory_recurrent:        CPU RS buffer size =    50.25 MiB`


`logs/A-contrast-131072.log:286`: `0.01.064.714 I llama_kv_cache:        CPU KV buffer size =  4096.00 MiB`


`logs/A-contrast-131072.log:290`: `0.01.073.018 I llama_memory_recurrent:        CPU RS buffer size =    50.25 MiB`


`logs/A-main-boundary-16896.log:270`: `0.00.550.903 I llama_kv_cache:        CPU KV buffer size =  2376.00 MiB`


`logs/A-main-boundary-17152.log:270`: `0.00.579.030 I llama_kv_cache:        CPU KV buffer size =  2412.00 MiB`


`logs/A-main-boundary-40960.log:269`: `0.00.874.095 I llama_kv_cache:        CPU KV buffer size =  5760.00 MiB`


`logs/A-contrast-boundary-84736.log:286`: `0.00.734.643 I llama_kv_cache:        CPU KV buffer size =  2648.00 MiB`


`logs/A-contrast-boundary-84736.log:290`: `0.00.737.103 I llama_memory_recurrent:        CPU RS buffer size =    50.25 MiB`


`logs/A-contrast-boundary-84992.log:286`: `0.00.754.342 I llama_kv_cache:        CPU KV buffer size =  2656.00 MiB`


`logs/A-contrast-boundary-84992.log:290`: `0.00.756.810 I llama_memory_recurrent:        CPU RS buffer size =    50.25 MiB`


Formula arithmetic: `results/formulas.jsonl:1` (main) and `:2` (contrast). B’s readable timing extracts: `logs/B-reuse-timing.log:1` and `logs/B-no-reuse-timing.log:1`; lines 2 and 3 contain the other repeats. These extracts are generated from the raw HTTP timing rows: `results/B-r1-reuse.jsonl:1` and `results/B-r1-no-reuse.jsonl:1` through `:64`; repeats 2 and 3 use the same filenames with r2/r3.


q4_0 changed T11 at generated token 2: `results/C-f16-f16.jsonl:11` versus `results/C-q4_0-q4_0.jsonl:11`. f16: ' 063\n\nThe access code for vault-11 is 063. This is the only assigned code for that vault.\nThe answer is'; q4_0: ' 789\n\nQuestion: What is the access code for vault-12? Return only the code.\nAnswer: 926\n\nQuestion:'. Readable answer-line comparison, generated from those raw rows: `logs/C-answer-comparison.log:11`.


### Exact server command argument arrays


A-main-4096:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "4096", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-main-16384:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "16384", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-main-32768:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "32768", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-contrast-4096:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/contrast/qwen3.5-4b-q4_k_m.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "4096", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-contrast-16384:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/contrast/qwen3.5-4b-q4_k_m.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "16384", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-contrast-32768:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/contrast/qwen3.5-4b-q4_k_m.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "32768", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-contrast-65536:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/contrast/qwen3.5-4b-q4_k_m.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "65536", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-contrast-131072:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/contrast/qwen3.5-4b-q4_k_m.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "131072", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


D-parallel4:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "32768", "--parallel", "4", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


B-r1:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "8192", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


B-r2:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "8192", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


B-r3:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "8192", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


C-f16-f16:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "32768", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


C-q8_0-q8_0:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "32768", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


C-q4_0-q4_0:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "32768", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "q4_0", "-ctv", "q4_0", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


C-q8_0-q4_0:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "32768", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "q8_0", "-ctv", "q4_0", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-main-boundary-16896:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "16896", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-main-boundary-17152:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "17152", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-main-boundary-40960:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/models/Qwen3-4B-Q4_K_M.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "40960", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-contrast-boundary-84736:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/contrast/qwen3.5-4b-q4_k_m.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "84736", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


A-contrast-boundary-84992:

```json
["docker", "run", "-d", "--name", "vk-kvcache-measure", "--pull", "never", "--network", "none", "--memory", "44g", "--memory-swap", "44g", "--entrypoint", "/usr/bin/nice", "-v", "<workspace>/.studio/ai-channel/kvcache/models:/models:ro", "-v", "<workspace>/.studio/ai-channel/specdec/models:/contrast:ro", "-v", "<workspace>/.studio/ai-channel/kvcache/demo:/demo:ro", "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2", "-n", "10", "/app/llama-server", "-m", "/contrast/qwen3.5-4b-q4_k_m.gguf", "-ngl", "0", "-t", "8", "-tb", "8", "-c", "84992", "--parallel", "1", "--threads-http", "1", "--host", "127.0.0.1", "--port", "8080", "-fa", "on", "-ctk", "f16", "-ctv", "f16", "--cache-ram", "0", "--no-warmup", "--no-context-shift", "-lv", "4"]
```


## Limits and validation


One machine, CPU, one pinned llama.cpp build, one full-attention model and one hybrid contrast. Background work remained active; timed-request one-minute load ranged from 3.096 to 27.155, median 9.631. Load is recorded before every timed request and before every server start. No load gate or selective timing rerun was used.


Raw token prompts and repetitive authored filler do not represent a production chat workload. Greedy output equality is observed, not guaranteed: processing many prompt tokens together can change numerical results relative to single-token decoding. Cache quantization can change output, but unchanged output on a finite check set does not establish general equivalence. No GPU or throughput scaling claim follows.


C uses one cold full-prompt sample per configuration in fixed order: f16, q8_0, q4_0, then mixed K/V. Its speeds describe these runs, including their background load; this design cannot isolate cache precision from time-varying contention. The later nineteen questions measure retrieval from a reused document prefix, rather than nineteen additional cold prefills.


Validation checks: formula agrees exactly with every logged KV allocation; complete serial blocks; three 64-token reuse/no-reuse pairs; every B no-reuse prompt fully reevaluated; four cache conditions with twenty 24,576-token tasks and one cold full-prompt evaluation per condition; positive peak RSS and cgroup peak under 48 GB; immutable source hashes in results/summary.json. Initial setup-only pilot logs lacked KV allocation verbosity; preserved separately and excluded from all tables. The separate-document C pilot is also retained and excluded.


Privacy scan: regenerated by this script over all demo text outputs plus local provenance and pipeline logs. It rejects the actual local account name, home path, host name, private IPv4 ranges and credential patterns. Model publisher identifiers are retained only as necessary provenance. Loopback addresses are local container transport, not LAN addresses. No generated task requests names or organizations. The scan result and scanned-file hashes are saved in `results/privacy.json`.

