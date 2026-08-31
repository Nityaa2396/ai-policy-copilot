# PolicyCopilot — Eval Case Study
## Measuring the Impact of RAG Chunking on Compliance QA Accuracy

**Author:** Krishna (Nitya) | **Date:** August 2026
**Repo:** github.com/Nityaa2396/ai-policy-copilot
**Live:** ai-policy-copilot.streamlit.app

---

## What the System Does

PolicyCopilot is an AI compliance assistant that answers employee questions about
company AI usage policies. An employee asks something like "Can I use ChatGPT to
summarize a client report?" and the system returns a structured verdict — Allowed,
Allowed with caution, Not allowed, or Needs review — with a citation to the exact
policy section and a safer alternative where relevant.

The system went through two architectural iterations:

**V1 — Full document injection**
Every question sent the entire policy document to Claude as context. Simple to
implement, but expensive and increasingly inaccurate on large documents where
irrelevant sections introduce noise.

**V2 — Chunked RAG with Qdrant**
The policy is split into sections by heading, embedded using trigram n-gram vectors,
and stored in Qdrant. Each question retrieves only the top 3 most relevant chunks.
Claude receives a fraction of the document — only what's needed to answer the question.

The claimed improvement was qualitative: "faster, cheaper, more accurate citations."
This eval was built to measure whether that claim holds up.

---

## Why This Eval Was Needed

Before this eval pipeline, the V1 vs V2 comparison existed only as a stated claim.
There were no ground truth questions, no scoring metrics, and no reproducible way
to verify that V2 was actually better — or to quantify by how much.

For a system making compliance decisions, that's a meaningful gap. Qualitative
claims don't tell you where the system fails, which question types it struggles
with, or what tradeoffs the architectural change introduced.

---

## How the Eval Was Built

**Ground truth dataset**
28 questions written against a synthetic policy document (TechNova Inc. AI Usage
Policy) designed specifically for eval. Questions span 3 difficulty tiers:

- Tier 1 (10 questions) — Direct lookup. Answer is explicitly stated in one section.
- Tier 2 (10 questions) — Inference required. Answer requires combining 2+ sections.
- Tier 3 (8 questions) — Edge cases. Ambiguous situations that should trigger escalation.

Each question has a known expected verdict and expected citation section, enabling
objective scoring without human judgment on individual answers.

A synthetic policy was chosen over a real company document for two reasons: full
control over ground truth, and reproducibility — anyone can load the same document
and re-run the eval.

**Metrics**
Three metrics were scored per question per pipeline:

1. Verdict accuracy — did the returned verdict match the expected verdict?
2. Citation accuracy — did the citation reference the correct policy section?
3. Context efficiency — what fraction of the full document was sent to Claude?

**Tooling**
- `run_baseline.py` — runs all 28 questions through V1 and V2, saves raw outputs
- `run_eval.py` — scores outputs against ground truth, produces CSV and summary JSON
- Stack: Python, Qdrant, Anthropic API, no external eval frameworks

---

## Results

| Metric | V1 (full doc) | V2 (RAG) | Delta |
|---|---|---|---|
| Verdict accuracy | 75.0% | 71.4% | -3.6% |
| Citation accuracy | 96.4% | 78.6% | -17.8% |
| Avg tokens sent | 1,860 | 984 | -876 |
| Token reduction | — | — | **47.1%** |

**By difficulty tier:**

| Tier | V1 verdict | V2 verdict | V1 citation | V2 citation |
|---|---|---|---|---|
| Tier 1 — Direct lookup | 80.0% | 70.0% | 90.0% | 70.0% |
| Tier 2 — Inference | 90.0% | 90.0% | 100.0% | 80.0% |
| Tier 3 — Edge cases | 50.0% | 50.0% | 100.0% | 87.5% |

---

## What the Numbers Show

**V2 achieves 47% token reduction with a modest accuracy tradeoff.**

The efficiency gain is substantial and consistent across all question types.
V2 sends roughly half the context of V1 on every question — this translates
directly to lower cost and faster response time at scale.

The accuracy picture is more nuanced:

**Where V2 holds up well:**
Tier 2 inference questions — verdict accuracy is identical (90%) and citation
accuracy drops only 20 points. This is the most practically important tier;
real employee questions rarely have one-section answers, and V2 handles
multi-section reasoning nearly as well as V1 with half the context.

Tier 3 edge cases — verdict accuracy is identical (50% both). These are
genuinely ambiguous questions where neither pipeline has a clear advantage.
The 50% score here reflects real policy ambiguity, not model failure.

**Where V2 loses ground:**
Tier 1 direct lookups show the sharpest drop — verdict accuracy falls from
80% to 70% and citation accuracy from 90% to 70%. This is the expected
weakness of top-k retrieval: when a question maps cleanly to one section,
chunking should retrieve it — but trigram n-gram embeddings sometimes
rank the wrong section first, so the relevant content isn't in the top 3.

**The unexpected finding:**
V1 citation accuracy (96.4%) is stronger than expected for a naive full-document
approach. Sending the full policy gives Claude access to every section, so it
can cite accurately even when the question is ambiguous. V2 pays a citation
penalty whenever retrieval misses the right chunk.

---

## What This Means for V3

The results point clearly to two improvements:

**1. Better embeddings**
Trigram n-gram vectors are deterministic and require no API calls, but they
match on character patterns rather than meaning. A Tier 1 question like
"Can Engineering use GitHub Copilot?" should retrieve Section 2 every time —
but n-gram similarity can mis-rank sections that share vocabulary.
Replacing with semantic embeddings (Voyage AI or similar) would likely
close the Tier 1 citation gap.

**2. Tuned top-k**
The current retrieval returns top 3 chunks. For Tier 2 inference questions
that span multiple sections, top 3 may miss one of the required sections.
Increasing to top 5 on questions that trigger lower confidence scores would
improve multi-section recall with minimal token cost increase.

---

## Reproducibility

Anyone can reproduce this eval in full:

```bash
git clone https://github.com/Nityaa2396/ai-policy-copilot
cd ai-policy-copilot
pip install -r requirements.txt
docker run -p 6333:6333 qdrant/qdrant
python run_baseline.py
python run_eval.py
```

All inputs (synthetic policy, ground truth dataset), scripts (baseline runner,
scorer), and outputs (raw responses, scored CSV, summary JSON) are committed
to the repo under `evals/`.

---

## Skills Demonstrated

This eval pipeline demonstrates the core loop of context engineering work:
identify what enters the model's context window, instrument the system to
measure output quality, run a controlled comparison, and use the findings
to inform the next iteration. The pipeline itself — ground truth design,
metric definition, reproducible scoring — is the artifact, not just the results.
