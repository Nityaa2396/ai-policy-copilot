"""
run_v4_eval.py
Measures three retrieval arms with REAL API token usage (not len//4 estimates),
all using the engine's own system prompt so the comparison is like-for-like:

  fulldoc  - entire policy in every prompt (V1-style)
  fixedk3  - Qdrant top_k=3 every time (V3)
  dynamic  - classifier picks top_k in {1,2,3} (V4); classifier call tokens counted

Saves evals/results/arm_<name>.json in the same row schema as v1/v2 outputs
(plus real token fields). Prints token and verdict-accuracy summary.

Run from the ai-policy-copilot root:  python run_v4_eval.py
"""
from __future__ import annotations

import json
import os
import time
from collections import Counter
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

from src.compliance_engine import (  # noqa: E402
    MODEL, SYSTEM_PROMPT, _build_user_message, _extract_text, _parse_json,
    _normalize_verdict, check_compliance,
)

POLICY_PATH = Path("evals/synthetic_policy.md")
DATASET_PATH = Path("evals/eval_dataset.json")
RESULTS_DIR = Path("evals/results")


def base_row(item):
    return {
        "id": item["id"], "tier": item["tier"], "question": item["question"],
        "expected_verdict": item["expected_verdict"],
        "expected_citation_section": item["expected_citation_section"],
    }


def run_fulldoc(item, policy_text, client):
    user = _build_user_message(item["question"], policy_text, True)
    msg = client.messages.create(
        model=MODEL, max_tokens=1024, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
    )
    p = _parse_json(_extract_text(msg))
    return {
        "verdict": _normalize_verdict(p.get("verdict", "needs_review")),
        "citation": str(p.get("citation", "")),
        "why": str(p.get("why", "")),
        "safer_alternative": str(p.get("safer_alternative", "")),
        "needs_human_review": bool(p.get("needs_human_review", False)),
        "top_k": None, "chunks_retrieved": 0,
        "classifier_input_tokens": 0, "classifier_output_tokens": 0,
        "main_input_tokens": msg.usage.input_tokens,
        "main_output_tokens": msg.usage.output_tokens,
    }


def run_rag(item, policy_text, client, fixed_k):
    trace = {}
    r = check_compliance(item["question"], policy_text, client=client,
                         trace=trace, fixed_top_k=fixed_k)
    return {
        "verdict": r.verdict, "citation": r.citation, "why": r.why,
        "safer_alternative": r.safer_alternative,
        "needs_human_review": r.needs_human_review, **trace,
    }


def run_arm(name, dataset, policy_text, client):
    print(f"\n--- arm: {name} ---")
    rows = []
    for item in dataset:
        print(f"  {item['id']}: {item['question'][:55]}...")
        row = base_row(item)
        try:
            if name == "fulldoc":
                res = run_fulldoc(item, policy_text, client)
            elif name == "fixedk3":
                res = run_rag(item, policy_text, client, fixed_k=3)
            else:
                res = run_rag(item, policy_text, client, fixed_k=None)
            row.update(res)
            row["total_input_tokens"] = res["main_input_tokens"] + res["classifier_input_tokens"]
            row["total_output_tokens"] = res["main_output_tokens"] + res["classifier_output_tokens"]
            row["tokens_sent"] = row["total_input_tokens"]
            row["error"] = None
        except Exception as e:  # keep going; record the failure
            print(f"    ERROR: {e}")
            row.update({"verdict": "", "citation": "", "why": "", "safer_alternative": "",
                        "needs_human_review": False, "top_k": None, "chunks_retrieved": 0,
                        "classifier_input_tokens": 0, "classifier_output_tokens": 0,
                        "main_input_tokens": 0, "main_output_tokens": 0,
                        "total_input_tokens": 0, "total_output_tokens": 0,
                        "tokens_sent": 0, "error": str(e)})
        row["arm"] = name
        rows.append(row)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / f"arm_{name}.json").write_text(json.dumps(rows, indent=2))
        time.sleep(0.5)
    return rows


def norm(v):
    return (v or "").strip().lower().replace(" ", "_").replace("-", "_")


def summarize(name, rows):
    ok = [r for r in rows if not r["error"]]
    n = len(ok) or 1
    avg = lambda k: sum(r[k] for r in ok) / n
    acc = sum(norm(r["verdict"]) == norm(r["expected_verdict"]) for r in ok) / n
    print(f"\n{name}: {len(ok)}/{len(rows)} ok")
    print(f"  verdict accuracy        : {acc * 100:.1f}%")
    print(f"  avg input tokens (main) : {avg('main_input_tokens'):.0f}")
    print(f"  avg input tokens (clf)  : {avg('classifier_input_tokens'):.0f}")
    print(f"  avg input tokens (total): {avg('total_input_tokens'):.0f}")
    print(f"  avg output tokens       : {avg('total_output_tokens'):.0f}")
    if name == "dynamic":
        print(f"  top_k chosen            : {dict(sorted(Counter(r['top_k'] for r in ok).items()))}")
        by_tier = {}
        for r in ok:
            by_tier.setdefault(r["tier"], []).append(r["top_k"])
        for t, ks in sorted(by_tier.items(), key=lambda x: str(x[0])):
            print(f"    tier {t}: avg top_k {sum(ks)/len(ks):.2f}")


def main():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=key)
    policy_text = POLICY_PATH.read_text(encoding="utf-8")
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    print(f"Policy: {len(policy_text)} chars | Questions: {len(dataset)}")

    all_rows = {}
    for name in ("fulldoc", "fixedk3", "dynamic"):
        all_rows[name] = run_arm(name, dataset, policy_text, client)
        summarize(name, all_rows[name])

    print("\nSaved: evals/results/arm_fulldoc.json, arm_fixedk3.json, arm_dynamic.json")
    print("Next: score citations with run_eval.py (verdict accuracy above is a quick check).")


if __name__ == "__main__":
    main()
