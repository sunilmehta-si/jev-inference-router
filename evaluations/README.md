# Evaluation method and results

The fixed corpus in `cases.json` contains 24 synthetic, manually labeled English
questions: eight general explanations, eight project-document questions, and eight
requests with missing context or demands to execute changes. This intentionally
small demonstration suite is not independently labeled or representative of all
production traffic. It was not expanded or relabeled after seeing the results.

`make evaluate-live` evaluates all cases serially, with three comparators:

1. Jev selects a route, estimates missing context, and scores retrieved passages.
   Python applies the fixed confidence and relevance gates.
2. Keyword rules classify questions with no hosted API call.
3. Local Qwen sees the route descriptions and the same candidate passages, and emits
   a JSON route label. Invalid JSON or provider failures count as failures.

Jev also repeats each case with Choice options reversed. These extra calls measure
selected-route stability; they are excluded from primary latency and accuracy but
included in estimated Jev cost. No Qwen self-reported confidence is compared with
Jev probabilities. The confidence threshold remains 0.65 throughout.

## Recorded run: 6 October 2026

| System | Valid requests | Matches | p50 | p95 |
|---|---:|---:|---:|---:|
| Jev with policy | 24/24 | 22/24 | 387.45 ms | 491.31 ms |
| Qwen2.5-7B-Instruct 4-bit | 24/24 | 21/24 | 1692.50 ms | 3239.72 ms |
| Rules | 24/24 | 22/24 | Not measured | Not measured |

Jev's 14 accepted non-clarification routes all matched the labels. That conditional
accuracy excludes abstentions and intentionally clarified requests; do not treat it
as overall accuracy. Two expected retrieval cases (`docs-04` and `docs-07`) were
selected correctly by Jev but gated to clarification due to confidence 0.59 and 0.64.
The small sample does not justify lowering thresholds to improve this score.

The keyword baseline failed `clarify-06` and `clarify-08`, sending them to generation.
The local Qwen baseline missed three documentation routes. Both baselines and policy
outcomes are included even where they do not favor Jev.

There were 0 selected-route changes across 24 reversed-option checks. This checks
one kind of stability, not all permutations or robustness against adversarial inputs.

The estimated cost of all 48 Jev calls is $0.00213503 at the documented $0.042 per
million input tokens. This uses API-reported usage; failed attempts or retries may
incur charges not present in successful-response usage. Your account terms may differ.

## Reproducibility and interpretation

`live-results.json` records SDK/Python/model versions, thresholds, per-case decisions,
probabilities, token usage, latency, reversed decisions, and confusion matrices.
`demo-results.json` uses deterministic fixtures; its scores are not model predictions
and zero recorded decision timing does not mean zero real computation cost.
`end-to-end.json` records successful checks for four application routes, including
actual Qwen generation and retrieval. It does not store raw generated answers.

The first attempted Qwen comparison found the companion gateway stopped. That
connectivity failure was diagnosed, the engine and gateway were restarted, and the
entire unchanged evaluation was rerun. The published live report is the completed
run, not the failed connectivity attempt. The synthetic corpus and thresholds were
unchanged. An initial Jev-only run produced the same 22/24 policy matches.

Latency is client-observed, including network round trip from India. Calls are serial,
without load testing, and Qwen may reuse prompt prefixes. p50 and p95 use linear
interpolation. Jev and Qwen have different output contracts. This is not evidence
that either universally outperforms the other.

Future work: independent held-out incident data, paraphrases, prompt-injection cases,
separate calibration/tuning splits, reliability plots, and answer/citation evaluation.
Do not use the same examples both to tune thresholds and claim held-out accuracy.
