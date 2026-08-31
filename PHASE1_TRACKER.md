# PolicyCopilot — Phase 1 Eval Pipeline
## Master Tracker

**Goal:** Add a reproducible, benchmarked eval pipeline to PolicyCopilot.
Turn qualitative claim ("V2 is better") into a measured result with real numbers.

**Target sentence when done:**
> "V2 improved citation accuracy by X% and reduced context tokens by Y%
> on a 28-question eval set across three difficulty tiers."

---

## Project State at Phase 1 Start

### What exists (deployed at ai-policy-copilot.streamlit.app)

```
User uploads/pastes/fetches a policy document
        ↓
V2: chunk_by_heading() — splits doc by markdown headings
        ↓
Trigram n-gram embeddings on each chunk
        ↓
Qdrant (local, in-memory) stores chunks with policy_id
        ↓
User asks question → question embedded → top 3 chunks retrieved
        ↓
Only those 3 chunks sent to Claude (not full document)
        ↓
Claude returns: verdict + citation + alternatives + risk tags
```

**V1 (baseline, no longer default):**
Full document injected into Claude context on every question.
No chunking, no retrieval — just paste everything and ask.

### What does NOT exist yet (what we're building)
```
evals/
  eval_dataset.json      — 25-30 ground truth QA pairs
  synthetic_policy.md    — the policy doc used for eval
  run_eval.py            — eval harness script (runs V1 + V2, scores both)
  results/
    v1_outputs.json      — raw V1 answers
    v2_outputs.json      — raw V2 answers
    eval_results.csv     — scored comparison table
docs/
  eval_case_study.md     — write-up for portfolio + WAI BYOP submission
```

The eval layer sits **outside and alongside** the main app.
It does not change how the app works for end users.
It measures whether the system does what we claim.

---

## Week 1 Tasks — Ground Truth + Baseline

### Step 1: Write the synthetic policy document
- [ ] Create `evals/synthetic_policy.md`
- [ ] 6-8 sections: approved tools, data handling, employee roles,
      prohibited uses, escalation process, vendor approval, exceptions
- [ ] Each section must have explicit, quotable rules (so citation accuracy is measurable)

**Why synthetic over real:** Full control over ground truth.
No IP concerns. Anyone can reproduce the eval.

### Step 2: Write the ground truth dataset
- [ ] Create `evals/eval_dataset.json`
- [ ] 25-30 QA pairs total across 3 difficulty tiers:

**Tier 1 — Direct lookup (10 questions)**
Answer is explicitly stated in one section.
Example: "Can Sales use ChatGPT for drafting emails?"
Expected: exact section + clear verdict.

**Tier 2 — Inference required (10 questions)**
Answer requires combining information from 2+ sections.
Example: "Can a contractor use an approved tool on client data?"
Expected: reasoned verdict with multiple citations.

**Tier 3 — Edge cases (8-10 questions)**
Ambiguous situations that should trigger "Needs review."
Example: "Can I use an AI tool that's not on the approved list
if my manager verbally approved it?"
Expected: escalation verdict, not a hard allow/deny.

**Dataset format:**
```json
[
  {
    "id": "q001",
    "tier": 1,
    "question": "Can the Engineering team use GitHub Copilot?",
    "expected_verdict": "Allowed",
    "expected_citation_section": "Section 2 — Approved Tools",
    "expected_citation_text": "exact quote from policy",
    "notes": "Straightforward lookup, Copilot is listed explicitly"
  }
]
```

### Step 3: Run V1 baseline
- [ ] Pipe all 25-30 questions through V1 (full-doc injection)
- [ ] Capture for each: answer returned, section cited, tokens sent
- [ ] Save as `evals/results/v1_outputs.json`

### Step 4: Run V2 baseline
- [ ] Same questions through V2 (chunked RAG)
- [ ] Capture: chunks retrieved, tokens sent, answer returned, section cited
- [ ] Save as `evals/results/v2_outputs.json`

**End of Week 1 deliverable:**
`eval_dataset.json` complete. Both output files saved.

---

## Week 2 Tasks — Eval Harness + Metrics

### Step 5: Build eval_runner.py
- [ ] Create `evals/run_eval.py`
- [ ] Modular functions — one per metric
- [ ] Takes v1_outputs.json + v2_outputs.json as input
- [ ] Outputs eval_results.csv

**Code structure:**
```python
def score_citation_accuracy(output, ground_truth):
    # Did it cite the correct section?

def score_faithfulness(output, retrieved_chunks):
    # Did the answer only use info from retrieved chunks?

def score_context_efficiency(output):
    # tokens_sent / total_document_tokens

def run_eval(v1_outputs, v2_outputs, ground_truth):
    # Score all questions on all metrics
    # Return comparison dataframe
```

### Step 6: Implement 3 core metrics
- [ ] Citation accuracy — correct section cited (yes/no per question)
- [ ] Faithfulness — answer grounded in retrieved chunks only
- [ ] Context efficiency — tokens sent vs total doc size

### Step 7: Score and analyze
- [ ] Run harness on both output files
- [ ] Produce eval_results.csv with all scores
- [ ] Find: where V2 wins, where it ties, any cases V2 loses
- [ ] Document findings honestly — losses are findings, not failures

**End of Week 2 deliverable:**
`run_eval.py` runnable. `eval_results.csv` with real numbers.

---

## Week 2.5 Tasks — Portfolio Packaging

### Step 8: Write eval case study
- [ ] Create `docs/eval_case_study.md`
- [ ] 600-900 words covering:
  - What the system does
  - Why V1 had gaps
  - How the eval was designed
  - What the numbers showed
  - What V2 does better, and where it doesn't
  - What you'd do next (V3 direction)

### Step 9: Update repo structure
- [ ] Add /evals folder with README explaining how to reproduce
- [ ] Update main README with eval results table
- [ ] Architecture diagram updated to show eval layer

### Step 10: LinkedIn post
- [ ] Tell the process story, not just the outcome
- [ ] Include one unexpected finding from the eval
- [ ] Link to repo

**End of Phase 1 deliverable:**
PolicyCopilot with reproducible eval pipeline.
Research-credible for WAI BYOP submission.
Actual numbers in the portfolio.

---

## Skills Demonstrated by Phase 1

| Skill | FDE relevance |
|---|---|
| Eval harness engineering | Core — how you prove a system works |
| Ground truth dataset design | Core — how you define "correct" |
| RAG pipeline instrumentation | Core — observing what enters the context window |
| Context efficiency measurement | Context engineering foundation |
| Technical write-up with findings | Client communication in FDE |
| Reproducible research | Research credibility for WAI BYOP |

---

## Progress Log

| Date | What was done | Files created/updated |
|---|---|---|
| [today] | Phase 1 tracker created. Project state documented. | PHASE1_TRACKER.md |
| | | |

*Update this log every session before closing.*

---

## Notes

- Stack: Python, Qdrant, Anthropic API, pandas — all existing
- Repo: github.com/Nityaa2396/ai-policy-copilot
- Deployed: ai-policy-copilot.streamlit.app
- Phase 2 (new FDE showcase project) begins after Phase 1 is zipped
