# PolicyCopilot — Eval Case Study
## Iterative RAG Improvement: V1 → V2 → V3

**Author:** Nitya | **Updated:** September 2026
**Repo:** github.com/Nityaa2396/ai-policy-copilot
**Live:** ai-policy-copilot.streamlit.app

---

## What the System Does

PolicyCopilot is an AI compliance assistant that answers employee questions about
company AI usage policies. An employee asks something like "Can I use ChatGPT to
summarize a client report?" and the system returns a structured verdict — Allowed,
Allowed with caution, Not allowed, or Needs review — with a citation to the exact
policy section and a safer alternative where relevant.

The system went through three architectural iterations, each measured against the
same ground truth eval dataset.

---

## The Three Versions

**V1 — Full document injection**
Every question sent the entire policy document to Claude as context. Simple to
implement, high citation accuracy, but expensive — every question pays the full
document token cost regardless of how simple the question is.

**V2 — Chunked RAG with trigram n-gram embeddings**
The policy is split into sections by heading and stored in Qdrant. Each question
retrieves only the top 3 most relevant chunks using trigram n-gram vectors —
character-pattern matching rather than semantic similarity. Achieved 47% token
reduction but introduced a citation accuracy gap because trigram embeddings
sometimes retrieved the wrong sections.

**V3 — Chunked RAG with Voyage AI semantic embeddings**
Same chunking and retrieval architecture as V2, but replaced trigram n-gram
vectors with Voyage AI `voyage-3` semantic embeddings. Semantic similarity
matches on meaning, not character patterns — closing the retrieval gap that
caused V2's citation accuracy drop.

---

## Eval Design

**Ground truth dataset**
28 questions written against a synthetic policy document (TechNova Inc. AI Usage
Policy). Questions span 3 difficulty tiers:

- Tier 1 (10 questions) — Direct lookup. Answer is explicitly stated in one section.
- Tier 2 (10 questions) — Inference required. Answer requires combining 2+ sections.
- Tier 3 (8 questions) — Edge cases. Ambiguous situations that should trigger escalation.

**Metrics**
- Verdict accuracy — did the returned verdict match the expected verdict?
- Citation accuracy — did the citation reference the correct policy section?
- Context efficiency — tokens sent relative to full document baseline

**Tooling**
- `run_baseline.py` — runs all 28 questions through V1 and V2/V3, saves raw outputs
- `run_eval.py` — scores outputs against ground truth, produces CSV and summary JSON
- Stack: Python, Qdrant Cloud, Anthropic API, Voyage AI

---

## Results

### Overall

| Metric | V1 (full doc) | V2 (trigram RAG) | V3 (semantic RAG) |
|---|---|---|---|
| Verdict accuracy | 75.0% | 71.4% | **78.6%** |
| Citation accuracy | 96.4% | 78.6% | **96.4%** |
| Avg tokens sent | 1,860 | 984 | 982 |
| Token reduction | — | 47.1% | **47.2%** |

### By difficulty tier

**Verdict accuracy:**

| Tier | V1 | V2 | V3 |
|---|---|---|---|
| Tier 1 — Direct lookup | 80.0% | 70.0% | 80.0% |
| Tier 2 — Inference | 90.0% | 90.0% | 90.0% |
| Tier 3 — Edge cases | 50.0% | 50.0% | 62.5% |

**Citation accuracy:**

| Tier | V1 | V2 | V3 |
|---|---|---|---|
| Tier 1 — Direct lookup | 90.0% | 70.0% | 100.0% |
| Tier 2 — Inference | 100.0% | 80.0% | 100.0% |
| Tier 3 — Edge cases | 100.0% | 87.5% | 87.5% |

---

## What the Numbers Show

### V2 → V3: The embedding upgrade

**Citation accuracy fully recovered — from 78.6% to 96.4%**, matching V1 exactly.
Token efficiency is unchanged at 47.2% reduction. V3 achieves the original goal:
same efficiency as V2, same accuracy as V1.

The root cause of V2's citation gap was confirmed: trigram n-gram embeddings match
on character patterns, not meaning. A question like "Can Engineering use GitHub
Copilot?" shares few character trigrams with "Section 2 — Approved AI Tools" even
though that is exactly the right section. Voyage AI semantic embeddings understand
that the question is about approved tools and retrieve the correct section.

**Verdict accuracy improved to 78.6%** — better than both V1 (75%) and V2 (71.4%).
The Tier 3 edge case improvement from 50% to 62.5% is particularly notable: semantic
retrieval surfaces more nuanced policy sections that help Claude reason about
ambiguous situations.

**Tier 1 citation accuracy reached 100%** — up from 70% in V2 and 90% in V1.
Direct lookup questions now retrieve the exact right section every time.

### The token efficiency story

V3 sends 982 avg tokens vs V1's 1,860 — a 47.2% reduction — while matching V1's
accuracy. The token count did not change significantly between V2 and V3 because
the chunking strategy is the same: top 3 chunks. What changed is which chunks are
retrieved. Better retrieval means Claude gets the right context within the same
token budget.

This is the key insight of context engineering: the goal is not to minimize tokens
at all costs — it is to maximize the information density of what enters the context
window. V3 achieves this by retrieving semantically relevant chunks rather than
character-pattern matches.

---

## What's Still Open: V4 Direction

V3 sends top 3 chunks on every question regardless of complexity. A Tier 1 direct
lookup question has its answer in one section, but still receives 3 chunks. This
wastes tokens and introduces potential noise from the less relevant chunks.

**V4 target: dynamic top-k based on question complexity**

The proposal is to classify each question before retrieval and send:
- Tier 1 (direct lookup) → top 1 chunk
- Tier 2 (inference) → top 2 chunks
- Tier 3 (edge cases) → top 3 chunks

Expected outcome: 20-30% additional token reduction on Tier 1 questions with
minimal accuracy impact, since the right answer is in a single section.

The risk: misclassifying a Tier 2 question as Tier 1 would send insufficient context,
potentially dropping verdict accuracy. The eval pipeline exists to measure exactly
this tradeoff before any change ships.

---

## Reproducibility

Anyone can reproduce this eval in full:

```bash
git clone https://github.com/Nityaa2396/ai-policy-copilot
cd ai-policy-copilot
pip install -r requirements.txt
python run_baseline.py
python run_eval.py
```

Required environment variables: `ANTHROPIC_API_KEY`, `QDRANT_URL`,
`QDRANT_API_KEY`, `VOYAGE_API_KEY`.

All inputs (synthetic policy, ground truth dataset), scripts (baseline runner,
scorer), and outputs (raw responses, scored CSV, summary JSON) are committed
to the repo under `evals/`.

---

## Skills Demonstrated

This eval pipeline demonstrates the core loop of context engineering work:
identify what enters the model's context window, instrument the system to
measure output quality, run a controlled comparison, and use the findings
to inform the next iteration.

The three-version arc — V1 baseline, V2 efficiency gain with accuracy tradeoff,
V3 closes the gap with semantic embeddings — shows iterative, measurement-driven
improvement. Each version was evaluated against the same 28-question ground truth
dataset, making the comparison reproducible and the claims verifiable.

The token efficiency gain (47.2% reduction) with accuracy parity (96.4% citation,
78.6% verdict) is the headline result. The V4 direction (dynamic top-k) is the
next measurable hypothesis.