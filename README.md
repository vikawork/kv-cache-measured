# KV cache, measured: what long context costs in memory

A measurement by [Vikawork](https://vikawork.com/). A transformer keeps the keys and values of every token it has
seen so it does not recompute them for the next token. We measured how much memory that cache takes per token,
how much time reusing it saves, and what changes when the cache is stored in 8 or 4 bits.

Everything ran locally on 14 November 2026 on a desktop processor (16 cores), CPU only, in a pinned llama.cpp build
(`full-b12211`). Main model: Qwen3-4B, the publisher's Q4_K_M GGUF, a dense model with full attention in all 36
layers. Contrast: Qwen3.5-4B (Q4_K_M), a hybrid model with full attention in 8 of its 32 runtime layers.

- Qwen3-4B allocates 147,456 bytes of f16 cache per token (2 × 36 layers × 8 KV heads × 128 × 2 bytes). Every
  logged allocation matches that formula exactly. At 32,768 tokens the cache is 4.5 GiB.
- The cache outgrows the 2.50 GB weight file at about 16,936 tokens; runs at 16,896 and 17,152 tokens bracket it.
- The hybrid contrast allocates 32,768 bytes per token, because only its 8 full-attention layers keep a cache. Its
  cache passes its weight file at about 84,944 tokens.
- Reusing the cache: a 4,096-token prompt plus 64 generated tokens took 23.4 s. Recomputing the whole growing prompt
  for each of the 64 tokens took 1,290 s (medians of three repeats). The output was identical in all three.

| Cache (K/V) | Size at 32,768 tokens | First answer line correct | Same text as f16 | Median generation, tokens/s |
| --- | ---: | ---: | ---: | ---: |
| f16/f16 | 4.50 GiB | 19 of 20 | 20 of 20 | 4.08 |
| q8_0/q8_0 | 2.39 GiB | 20 of 20 | 12 of 20 | 2.27 |
| q4_0/q4_0 | 1.27 GiB | 20 of 20 | 1 of 20 | 3.93 |
| q8_0/q4_0 | 1.83 GiB | 20 of 20 | 12 of 20 | 2.65 |

The retrieval check is one authored 24,576-token ledger with twenty codes at different depths and twenty
questions, the same prompts for every cache type. These are authored checks, not a benchmark. No condition passed
the strict answer-only check (0 of 20 each): the model kept writing after the code.

Other work was running on the machine (one-minute load 3.1 to 27.2 during timed requests), and the quantized-cache
speeds come from one run each in a fixed order, so they do not isolate the effect of cache precision. One machine,
one build, two models.

[REPORT.md](REPORT.md) has every table, the formulas, every server command, the per-question outputs and the
limits. It and `results/summary.json` are written by `summarize.py` from `results/*.jsonl` and `logs/`.

## What is here

- `setup.py`, `run.py`, `supplement.py`, `client.py`, `run-all.py`, `summarize.py`: the harness. Python standard
  library only. `client.py` runs inside the container and talks only to the server on its own loopback.
- `fixtures/`: the authored ledger text, its token IDs, the reuse prompt and the scoring policy.
- `results/`: raw measurements (JSONL), `summary.json`, `formulas.jsonl`, and `privacy.json` (the harness's own scan).
- `logs/`: llama-server logs for every run, with allocation-level verbosity.
- `provenance/`: model hashes and GGUF metadata (`models.json`), the publisher's licence and gating status
  (`publisher.json`), and the contrast model's conversion record (`contrast-conversion-setup.json`).
- `pilot-separate-documents/protocol-change.json`: the protocol change recorded before any quantized-cache run.

Not included: model weights, the Docker image, caches, and the excluded pilot runs.

## Paths in the report

The report was written inside a larger repository. Its paths map to this repository as follows.

| In REPORT.md | Here |
| --- | --- |
| `../provenance/` | `provenance/` |
| `.studio/ai-channel/specdec/provenance/setup.json` | `provenance/contrast-conversion-setup.json` |
| `../pilot-separate-documents/protocol-change.json` | `pilot-separate-documents/protocol-change.json` |
| `../pilot/` | not included |

## Run it

You need Docker and HTTPS access to Hugging Face. Nothing is downloaded during measurement: containers run with
networking disabled.

1. Image: `docker pull ghcr.io/ggml-org/llama.cpp:full-b12211@sha256:8960de326dd60972cc4d442531f4efa006416d5896da2a39f0def0b55cbcb0c2`
2. Main model: `setup.py` downloads `Qwen3-4B-Q4_K_M.gguf` from `Qwen/Qwen3-4B-GGUF` at revision
   `bc640142c66e1fdd12af0bd68f40445458f3869b` (2,497,280,256 bytes, SHA-256
   `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`).
3. Contrast model: convert `Qwen/Qwen3.5-4B` at revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` with the same
   image's `convert_hf_to_gguf.py` (f16) and `llama-quantize` (Q4_K_M). The result should be 2,783,446,464 bytes with
   SHA-256 `6e1cdfd39c43ec66dc290b75013515ae5b8f738861a4f18234acca3b0602f680`. The exact commands and source-file
   hashes are in `provenance/contrast-conversion-setup.json`;
   [speculative-decoding-vs-quantization](https://github.com/vikawork/speculative-decoding-vs-quantization)'s
   `setup.py` does the same conversion.
4. `python3 setup.py`, then `python3 run-all.py` (runs `run.py`, `supplement.py`, `summarize.py`).

The scripts expect the original layout: this folder as `demo/` inside a work folder that also holds `models/` and
`provenance/`, with the contrast GGUF in a sibling `specdec/models/`. Change `WORK` in `setup.py` and the model paths
in `run.py` to run them elsewhere. One server runs at a time, CPU only, eight threads, nice 10, under a 44 GiB cgroup
limit with swap disabled. Completed blocks are skipped on a rerun.

## Licence and credits

Our code is under the MIT licence ([LICENSE](LICENSE)); the report, results and authored fixtures may be reused with
credit to Vikawork. Qwen3-4B and Qwen3.5-4B are Apache-2.0 models by the Qwen team; they are not redistributed here.
The logs are output of [llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT).

[SCAN.md](SCAN.md) records the privacy scan run before publishing.
