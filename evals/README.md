# PolicyCopilot — Eval Pipeline

This folder contains everything needed to reproduce the V1 vs V2 evaluation.

## What's here

```
evals/
  synthetic_policy.md      — policy document used for all eval questions
  eval_dataset.json        — 28 ground truth QA pairs across 3 tiers
  run_eval.py              — [TODO Week 2] eval harness script
  results/
    v1_outputs.json        — [TODO Week 1] raw V1 answers
    v2_outputs.json        — [TODO Week 1] raw V2 answers
    eval_results.csv       — [TODO Week 2] scored comparison table
```

## Why a synthetic policy?

Full control over ground truth. No IP concerns. Anyone can load
`synthetic_policy.md` into PolicyCopilot and reproduce every result.

## Dataset structure

28 questions across 3 difficulty tiers:

| Tier | Count | Description |
|---|---|---|
| 1 — Direct lookup | 10 | Answer is explicitly in one section |
| 2 — Inference required | 10 | Answer requires combining 2+ sections |
| 3 — Edge cases | 8 | Ambiguous — should trigger "Needs review" |

## Metrics (to be scored in run_eval.py)

- Citation accuracy — did it cite the correct section?
- Faithfulness — did the answer only use retrieved chunks?
- Context efficiency — tokens sent / total doc tokens

## How to reproduce (once run_eval.py is complete)

```bash
pip install anthropic qdrant-client pandas
python run_eval.py --policy evals/synthetic_policy.md \
                   --dataset evals/eval_dataset.json \
                   --output evals/results/
```
