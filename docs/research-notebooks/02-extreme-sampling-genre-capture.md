# Experiment notebook 02 — Extreme sampling and genre capture

> **Notebook status:** retrospective, post-hoc analysis of one ACS Workbench export. The export does not record a preregistered hypothesis, randomization, or operator-authored controls. The hypothesis below is a proposal for a future controlled run, not a historical claim.

## Record

| Field | Recorded value |
|---|---|
| Workbench experiment ID | `9a5c3199-9b2f-4ae0-b4a9-4b504e7399f4` |
| Workbench title (exact export value) | `weak Tweak (IFS exile-manager blend) sco` |
| Source export | `2026-10-30_extreme-sampling_genre-capture_batch-06.jsonl` |
| Created / last updated | 2026-10-30 19:50:37–19:55:35 UTC |
| Unique run IDs | 17 |
| Exact prompts | 15 |
| Run-level models | `trinity-truebase` (15); `llama-8b` (2) |
| Upstream model identifiers | `arcee-ai/Trinity-Large-TrueBase`; `meta-llama/Llama-3.1-8B` |

## Archival question and proposed hypothesis

**Question:** Under the recorded high-temperature and restricted-candidate configurations, what kinds of text are visible, and how often are records complete versus cancelled?

**H1 — proposed prospectively:** With a single prompt, model, seed protocol, token budget, and all non-temperature sampling controls fixed, increasing temperature may change the rate of lexical fragmentation. The present export cannot test this: the most extreme temperatures occur with different Top K, Min P, presence penalty, prompts, and mostly cancelled runs.

## Design and recorded settings

There are 17 unique generations: 4 marked `completed` and 13 marked `cancelled`. The 15 distinct prompt strings and the sampling configuration change across the run sequence. No operator-supplied control group is represented in the export.

| Parameter | Recorded values |
|---|---|
| Temperature | 6 distinct values: `1.0`, `2.0`, `2.2`, `2.200980989887877`, `12.0`, `32.200980989887874` |
| Top P | `1.0` in all 17 runs |
| Top K | `-1` (11 runs) or `1` (6 runs) |
| Min P | `0.0` (5), `0.12218974389217321` (8), `0.99999999999` (4) |
| Presence penalty | `0.0` (6), `0.21204210840219848` (3), `1.2120421084021984` (8) |
| Frequency penalty | `0.0` in all 17 runs |
| Repetition penalty | `1.0` in all 17 runs |
| Max tokens | `200` in all 17 runs |
| Seed mode | `random` in all 17; 17 distinct recorded integer seeds |
| Requested logprobs | `5` in 13 runs; not recorded in 4 |
| Returned logprob arrays | present in 13 runs |

The four completed runs all record `finish_reason: length` and `usage_source: upstream`. The 13 cancelled runs have no recorded finish reason and use `usage_source: tokenizer`. These status and usage distinctions are retained; a cancelled run with text is a partial record, not a completed sample.

## Observations

1. **Completion is uneven across this small batch.** Four of 17 runs are completed; 13 are cancelled. All four completed records are at temperature `1.0`. The data do not establish that temperature caused cancellation: prompt, model, Top K, Min P, penalties, and other configuration also differ, and there are few observations at the extremes.
2. **Two exact-prompt model pairs exist at temperature `1.0`.** Both pairs match their recorded non-model settings; one pair has both runs completed, while the other has a completed Llama run and a cancelled Trinity run. Their recorded integer seeds differ. This is useful for a cautious specimen comparison, not a same-seed model benchmark.
3. **A bare name turns into competing product descriptions.** Generation `0dd744b6-62a7-4286-a6f4-8875b799e949` continues the prompt `Zazie` as software copy and then recasts the name as a language-learning app. It is marked cancelled after 117 completion tokens reported by the tokenizer. This is a partial, documentary-sounding fragment; none of its product claims are verified.
4. **The highest recorded temperature is not a clean treatment.** The two runs at `32.200980989887874` are both cancelled, use `top_k: 1`, `min_p: 0.12218974389217321`, and the same presence-penalty value, and contain different prompts. A separate run at temperature `12.0` also has `top_k: 1` and a non-zero Min P. These configurations cannot isolate a temperature effect.
5. **A text fragment can look fluent while its record remains incomplete.** Some cancelled runs contain readable clauses or repeated short strings. Those textual features do not change their recorded status: all remain cancelled, with partial token counts and no finish reason.
6. **History lanes do not add specimens.** The export contains 13 ordinary snapshots and 2 comparison snapshots. All four comparison-lane `generation_id` values point to run IDs already present in `runs`; the pipeline therefore counts the 17 stable run IDs once, not 21 or more events.

## Limitations

- This is one short batch, with 17 runs and 15 exact prompts. It is not a factorial or repeated-measures design.
- Temperature is entangled with Top K, Min P, presence penalty, prompt, and model. The 13 cancellations create additional selection bias if only completed text is analyzed.
- Every seed is distinct; neither fixed-seed replication nor repeated sampling within a condition is present.
- Token usage is `upstream` for the four completed runs and `tokenizer` for all cancelled runs. Their counts should not be treated as one homogeneous tokenizer measurement.
- The export records settings, not their exact implementation semantics. In particular, the archive does not infer how the backend combines temperature, Top K, and Min P.
- “Genre capture” and related labels are editorial readings of text. The eight current seed annotations are AI-assisted, unreviewed, and not a validated coding instrument.
- Prompt strings may contain sensitive or emotionally intense material. The public interface masks common structured identifiers best-effort; the source and normalized dataset are preserved exactly. Review permission and privacy before publishing.

## Next controlled run (proposal)

Use one short, non-sensitive ambiguous prompt and one fixed model build. Vary only temperature across a preregistered grid; hold Top P, Top K, Min P, penalties, max tokens, prompt, and stop conditions constant. Run a shared fixed seed set for every temperature when supported, with repeated samples per cell. Record cancellation reason separately from completion status, and compare both intention-to-sample outcomes and completed-text outcomes. Have annotators blind to settings label genre capture, documentary normalization, and lexical disintegration before unblinding.
