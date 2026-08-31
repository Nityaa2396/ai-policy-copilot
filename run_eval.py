"""
Eval scorer for PolicyCopilot.

Scores v1_outputs.json and v2_outputs.json against ground truth in eval_dataset.json.
Produces evals/results/eval_results.csv with per-question scores and a summary.

Metrics:
  1. Verdict accuracy     — did the verdict match expected?
  2. Citation accuracy    — did the citation reference the correct section?
  3. Context efficiency   — tokens sent relative to full document baseline

Usage:
    python run_eval.py

Run from the root of ai-policy-copilot repo.
"""

from __future__ import annotations

import json
import csv
from pathlib import Path

DATASET_PATH = Path("evals/eval_dataset.json")
V1_PATH = Path("evals/results/v1_outputs.json")
V2_PATH = Path("evals/results/v2_outputs.json")
RESULTS_PATH = Path("evals/results/eval_results.csv")
SUMMARY_PATH = Path("evals/results/eval_summary.json")

POLICY_PATH = Path("evals/synthetic_policy.md")


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_full_doc_tokens() -> int:
    """Token count of full policy — used as efficiency baseline."""
    policy_text = POLICY_PATH.read_text(encoding="utf-8")
    system_prompt_approx = 400
    return len(policy_text) // 4 + system_prompt_approx


def score_verdict(output_verdict: str, expected_verdict: str) -> int:
    """1 if verdict matches expected, 0 otherwise."""
    def normalize(v: str) -> str:
        return v.strip().lower().replace(" ", "_").replace("-", "_")
    return int(normalize(output_verdict) == normalize(expected_verdict))


def score_citation(output_citation: str, expected_section: str) -> int:
    """
    1 if the expected section name appears in the citation, 0 otherwise.
    Case-insensitive, partial match allowed.
    Example: expected 'Section 2 — Approved AI Tools'
             output citation 'Section 2 — Approved AI Tools: Engineering team only'
             → match
    """
    if not output_citation or not expected_section:
        return 0

    citation_lower = output_citation.lower()

    # extract key identifiers from expected section
    # match on section number OR key words from section name
    expected_lower = expected_section.lower()

    # try direct substring match first
    if expected_lower in citation_lower:
        return 1

    # try matching section number alone (e.g. "section 2")
    parts = expected_lower.split("—")
    section_num = parts[0].strip()  # e.g. "section 2"
    if section_num and section_num in citation_lower:
        return 1

    # try matching key words from section title
    if len(parts) > 1:
        title_words = parts[1].strip().split()
        # require at least 2 meaningful words to match
        meaningful = [w for w in title_words if len(w) > 3]
        matches = sum(1 for w in meaningful if w in citation_lower)
        if matches >= 2:
            return 1

    return 0


def score_efficiency(tokens_sent: int, full_doc_tokens: int) -> float:
    """
    Efficiency score — lower tokens sent = higher score.
    Returns ratio of tokens saved vs full document.
    1.0 = sent nothing (impossible), 0.0 = sent full doc.
    Useful for comparing V1 vs V2 relative efficiency.
    """
    if full_doc_tokens == 0:
        return 0.0
    tokens_saved = max(0, full_doc_tokens - tokens_sent)
    return round(tokens_saved / full_doc_tokens, 3)


def build_lookup(dataset: list[dict]) -> dict[str, dict]:
    return {item["id"]: item for item in dataset}


def score_outputs(
    outputs: list[dict],
    ground_truth: dict[str, dict],
    full_doc_tokens: int,
    label: str,
) -> list[dict]:
    rows = []
    for output in outputs:
        qid = output["id"]
        gt = ground_truth.get(qid, {})

        verdict_score = score_verdict(
            output.get("verdict", ""),
            gt.get("expected_verdict", ""),
        )
        citation_score = score_citation(
            output.get("citation", ""),
            gt.get("expected_citation_section", ""),
        )
        efficiency = score_efficiency(
            output.get("tokens_sent", full_doc_tokens),
            full_doc_tokens,
        )

        rows.append({
            "id": qid,
            "tier": output.get("tier", ""),
            "question": output.get("question", ""),
            "pipeline": label,
            "expected_verdict": gt.get("expected_verdict", ""),
            "actual_verdict": output.get("verdict", ""),
            "verdict_correct": verdict_score,
            "expected_citation": gt.get("expected_citation_section", ""),
            "actual_citation": output.get("citation", ""),
            "citation_correct": citation_score,
            "tokens_sent": output.get("tokens_sent", 0),
            "efficiency_score": efficiency,
            "chunks_retrieved": output.get("chunks_retrieved", "N/A"),
            "error": output.get("error") or "",
        })

    return rows


def compute_summary(rows: list[dict], label: str) -> dict:
    subset = [r for r in rows if r["pipeline"] == label]
    total = len(subset)
    if total == 0:
        return {}

    verdict_acc = sum(r["verdict_correct"] for r in subset) / total
    citation_acc = sum(r["citation_correct"] for r in subset) / total
    avg_tokens = sum(r["tokens_sent"] for r in subset) / total
    avg_efficiency = sum(r["efficiency_score"] for r in subset) / total

    by_tier: dict[int, dict] = {}
    for tier in [1, 2, 3]:
        tier_rows = [r for r in subset if r["tier"] == tier]
        if tier_rows:
            by_tier[tier] = {
                "count": len(tier_rows),
                "verdict_accuracy": round(
                    sum(r["verdict_correct"] for r in tier_rows) / len(tier_rows), 3
                ),
                "citation_accuracy": round(
                    sum(r["citation_correct"] for r in tier_rows) / len(tier_rows), 3
                ),
            }

    return {
        "pipeline": label,
        "total_questions": total,
        "verdict_accuracy": round(verdict_acc, 3),
        "citation_accuracy": round(citation_acc, 3),
        "avg_tokens_sent": round(avg_tokens),
        "avg_efficiency_score": round(avg_efficiency, 3),
        "by_tier": by_tier,
    }


def save_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id", "tier", "question", "pipeline",
        "expected_verdict", "actual_verdict", "verdict_correct",
        "expected_citation", "actual_citation", "citation_correct",
        "tokens_sent", "efficiency_score", "chunks_retrieved", "error",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved {len(rows)} rows to {path}")


def print_report(v1_summary: dict, v2_summary: dict) -> None:
    print("\n" + "=" * 58)
    print("  PolicyCopilot — V1 vs V2 Eval Results")
    print("=" * 58)

    metrics = [
        ("Verdict accuracy", "verdict_accuracy", "{:.1%}"),
        ("Citation accuracy", "citation_accuracy", "{:.1%}"),
        ("Avg tokens sent", "avg_tokens_sent", "{:,}"),
        ("Avg efficiency score", "avg_efficiency_score", "{:.3f}"),
    ]

    print(f"\n{'Metric':<25} {'V1':>10} {'V2':>10} {'Delta':>10}")
    print("-" * 58)

    for label, key, fmt in metrics:
        v1_val = v1_summary.get(key, 0)
        v2_val = v2_summary.get(key, 0)

        if isinstance(v1_val, float) and "accuracy" in key:
            delta = v2_val - v1_val
            delta_str = f"{delta:+.1%}"
        elif key == "avg_tokens_sent":
            delta = v2_val - v1_val
            delta_str = f"{delta:+,}"
        else:
            delta = v2_val - v1_val
            delta_str = f"{delta:+.3f}"

        print(
            f"{label:<25} {fmt.format(v1_val):>10} {fmt.format(v2_val):>10} {delta_str:>10}"
        )

    print("\nBy tier:")
    print(f"  {'Tier':<8} {'V1 verdict':>12} {'V2 verdict':>12} {'V1 citation':>13} {'V2 citation':>13}")
    print("  " + "-" * 60)
    for tier in [1, 2, 3]:
        v1t = v1_summary.get("by_tier", {}).get(tier, {})
        v2t = v2_summary.get("by_tier", {}).get(tier, {})
        print(
            f"  Tier {tier:<4}"
            f" {v1t.get('verdict_accuracy', 0):>11.1%}"
            f" {v2t.get('verdict_accuracy', 0):>12.1%}"
            f" {v1t.get('citation_accuracy', 0):>12.1%}"
            f" {v2t.get('citation_accuracy', 0):>12.1%}"
        )

    print("\n" + "=" * 58)
    token_reduction = (
        (v1_summary["avg_tokens_sent"] - v2_summary["avg_tokens_sent"])
        / v1_summary["avg_tokens_sent"] * 100
        if v1_summary.get("avg_tokens_sent") else 0
    )
    print(f"  Token reduction V1 → V2: {token_reduction:.1f}%")
    print("=" * 58 + "\n")


def main() -> None:
    print("Loading files...")
    dataset = load_json(DATASET_PATH)
    v1_outputs = load_json(V1_PATH)
    v2_outputs = load_json(V2_PATH)
    ground_truth = build_lookup(dataset)
    full_doc_tokens = get_full_doc_tokens()

    print(f"  Full document token estimate: {full_doc_tokens:,}")
    print(f"  Scoring {len(v1_outputs)} V1 outputs and {len(v2_outputs)} V2 outputs...")

    v1_rows = score_outputs(v1_outputs, ground_truth, full_doc_tokens, "V1")
    v2_rows = score_outputs(v2_outputs, ground_truth, full_doc_tokens, "V2")
    all_rows = v1_rows + v2_rows

    save_csv(all_rows, RESULTS_PATH)

    v1_summary = compute_summary(all_rows, "V1")
    v2_summary = compute_summary(all_rows, "V2")

    summary = {"v1": v1_summary, "v2": v2_summary}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"  Saved summary to {SUMMARY_PATH}")

    print_report(v1_summary, v2_summary)
    print("Next step: review eval_results.csv for per-question breakdown.")
    print("Then: write docs/eval_case_study.md with your findings.")


if __name__ == "__main__":
    main()