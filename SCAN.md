# Privacy scan

Run on 15 November 2026 over every file in this repository before the first commit.

Searched for:

- the value of every key, token or secret variable in the measuring workspace's `.env` (compared inside the scan
  script; values never printed), and the key prefixes `sk-`, `AIza`, `ghp_`, `github_pat_`, `hf_`, `xox`, private-key
  blocks and bearer tokens;
- home-directory paths (`/home/...`, `/Users/...`), the account user name, the host name, and the committer's name
  and e-mail address;
- private IPv4 addresses (10.x, 172.16–31.x, 192.168.x);
- e-mail addresses, and processor and graphics-card model names.

Result: clean. Two patterns matched text that is not private and was left in place:

- The host name is a common English word that appears only in the phrase "desktop processor".
- The 10.x pattern matched llama.cpp log timestamps such as `10.09.359.784`.

Changes made for publication, after the harness's own scan (`results/privacy.json`):

- Line 8 of each of the 21 llama-server logs named the processor model; it now reads
  `[desktop processor, 16 cores]`. Those 21 files no longer match the hashes in `results/privacy.json`; nothing
  else in them changed.
- `provenance/contrast-conversion-setup.json` is a copy of the contrast model's conversion record with its processor
  field removed.

Every other file is byte-identical to the measurement output.
