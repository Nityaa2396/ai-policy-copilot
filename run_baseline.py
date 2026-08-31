"""
Baseline runner for PolicyCopilot eval pipeline.

Runs all questions in eval_dataset.json through V1 (full-doc) and V2 (RAG)
and saves raw outputs to evals/results/v1_outputs.json and v2_outputs.json.

Usage:
    python run_baseline.py

Requirements:
    - ANTHROPIC_API_KEY set in .env or environment
    - Qdrant running locally on port 6333 (for V2)
    - Run from the root of ai-policy-copilot repo
"""

from __future__ import annotations

import json
import os
import time
import hashlib
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

POLICY_PATH = Path("evals/synthetic_policy.md")
DATASET_PATH = Path("evals/eval_dataset.json")
RESULTS_DIR = Path("evals/results")

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a decision assistant for an internal AI usage policy.

You receive a user question describing an AI use case and the full policy text. You return a structured decision.

Rules you must follow:
- Ground every decision in the provided policy text. Never invent clauses or section numbers.
- Cite the exact section heading and, if present, the section number.
- Verdict must be one of:
  - "allowed" — the policy clearly permits the use and any stated conditions are already satisfied.
  - "allowed_with_caution" — permitted but the user should follow a condition or mitigate a stated risk.
  - "not_allowed" — the policy clearly prohibits it, or a hard precondition is unmet.
  - "needs_review" — the policy is silent, ambiguous, contradictory, or the facts are insufficient to decide.
- "why" must be 100 words or less, plain language, no hedging.
- "safer_alternative" must be non-empty when verdict is "not_allowed" or "allowed_with_caution"; otherwise use an empty string.
- "needs_human_review" is a boolean.

Output MUST be a single JSON object with exactly these keys and no others:
  "verdict": "allowed" | "allowed_with_caution" | "not_allowed" | "needs_review"
  "why": string
  "citation": string
  "safer_alternative": string
  "needs_human_review": boolean

Do not include any text outside the JSON object."""


def load_files() -> tuple[str, list[dict]]:
    policy_text = POLICY_PATH.read_text(encoding="utf-8")
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    return policy_text, dataset


def count_tokens(text: str) -> int:
    """Rough token estimate — 1 token per 4 characters."""
    return len(text) // 4


def build_user_message(question: str, context: str) -> str:
    return (
        f"<policy>\n{context.strip()}\n</policy>\n\n"
        f"<question>\n{question.strip()}\n</question>\n\n"
        "Return the JSON object described in the system prompt."
    )


def call_claude(question: str, context: str, client: Anthropic) -> tuple[dict, int]:
    """Call Claude and return parsed response + tokens sent."""
    user_message = build_user_message(question, context)
    tokens_sent = count_tokens(SYSTEM_PROMPT + user_message)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            raw = block.text
            break

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    start = raw.find("{")
    end = raw.rfind("}")
    parsed = json.loads(raw[start:end + 1])

    return parsed, tokens_sent


def run_v1(dataset: list[dict], policy_text: str, client: Anthropic) -> list[dict]:
    """V1 — sends full policy text to Claude on every question."""
    print("\n--- Running V1 (full-doc injection) ---")
    outputs = []

    for item in dataset:
        qid = item["id"]
        question = item["question"]
        print(f"  {qid}: {question[:60]}...")

        try:
            response, tokens_sent = call_claude(question, policy_text, client)
            result = {
                "id": qid,
                "tier": item["tier"],
                "question": question,
                "expected_verdict": item["expected_verdict"],
                "expected_citation_section": item["expected_citation_section"],
                "verdict": response.get("verdict", ""),
                "citation": response.get("citation", ""),
                "why": response.get("why", ""),
                "safer_alternative": response.get("safer_alternative", ""),
                "needs_human_review": response.get("needs_human_review", False),
                "tokens_sent": tokens_sent,
                "context_source": "full_document",
                "error": None,
            }
        except Exception as e:
            print(f"    ERROR: {e}")
            result = {
                "id": qid,
                "tier": item["tier"],
                "question": question,
                "expected_verdict": item["expected_verdict"],
                "expected_citation_section": item["expected_citation_section"],
                "verdict": "",
                "citation": "",
                "why": "",
                "safer_alternative": "",
                "needs_human_review": False,
                "tokens_sent": 0,
                "context_source": "full_document",
                "error": str(e),
            }

        outputs.append(result)
        time.sleep(0.5)

    return outputs


def run_v2(dataset: list[dict], policy_text: str, client: Anthropic) -> list[dict]:
    """V2 — uses Qdrant chunking via existing check_compliance()."""
    from src.compliance_engine import check_compliance
    from src.vector_store import search_chunks, index_policy, policy_is_indexed

    print("\n--- Running V2 (chunked RAG via Qdrant) ---")

    policy_id = hashlib.md5(policy_text.encode()).hexdigest()[:16]

    if not policy_is_indexed(policy_id):
        print(f"  Indexing policy into Qdrant (id: {policy_id})...")
        count = index_policy(policy_text, policy_id)
        print(f"  Indexed {count} chunks.")
    else:
        print(f"  Policy already indexed (id: {policy_id}), skipping.")

    outputs = []

    for item in dataset:
        qid = item["id"]
        question = item["question"]
        print(f"  {qid}: {question[:60]}...")

        try:
            chunks = search_chunks(question, policy_id, top_k=3)
            context_sent = "\n\n---\n\n".join(chunks) if chunks else policy_text
            tokens_sent = count_tokens(SYSTEM_PROMPT + build_user_message(question, context_sent))

            response = check_compliance(question, policy_text, client=client)

            result = {
                "id": qid,
                "tier": item["tier"],
                "question": question,
                "expected_verdict": item["expected_verdict"],
                "expected_citation_section": item["expected_citation_section"],
                "verdict": response.verdict,
                "citation": response.citation,
                "why": response.why,
                "safer_alternative": response.safer_alternative,
                "needs_human_review": response.needs_human_review,
                "tokens_sent": tokens_sent,
                "chunks_retrieved": len(chunks),
                "context_source": "qdrant_chunks",
                "error": None,
            }
        except Exception as e:
            print(f"    ERROR: {e}")
            result = {
                "id": qid,
                "tier": item["tier"],
                "question": question,
                "expected_verdict": item["expected_verdict"],
                "expected_citation_section": item["expected_citation_section"],
                "verdict": "",
                "citation": "",
                "why": "",
                "safer_alternative": "",
                "needs_human_review": False,
                "tokens_sent": 0,
                "chunks_retrieved": 0,
                "context_source": "qdrant_chunks",
                "error": str(e),
            }

        outputs.append(result)
        time.sleep(0.5)

    return outputs


def save_outputs(outputs: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(outputs, indent=2), encoding="utf-8")
    print(f"\n  Saved {len(outputs)} results to {path}")


def print_summary(label: str, outputs: list[dict]) -> None:
    total = len(outputs)
    errors = sum(1 for o in outputs if o.get("error"))
    avg_tokens = sum(o.get("tokens_sent", 0) for o in outputs) / total if total else 0
    print(f"\n{label} summary:")
    print(f"  Total questions : {total}")
    print(f"  Errors          : {errors}")
    print(f"  Avg tokens sent : {avg_tokens:.0f}")


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set. Add it to .env or export it.")

    client = Anthropic(api_key=api_key)

    print("Loading policy and dataset...")
    policy_text, dataset = load_files()
    print(f"  Policy: {len(policy_text)} chars")
    print(f"  Dataset: {len(dataset)} questions")

    v1_outputs = run_v1(dataset, policy_text, client)
    save_outputs(v1_outputs, RESULTS_DIR / "v1_outputs.json")
    print_summary("V1", v1_outputs)

    v2_outputs = run_v2(dataset, policy_text, client)
    save_outputs(v2_outputs, RESULTS_DIR / "v2_outputs.json")
    print_summary("V2", v2_outputs)

    print("\nDone. Both output files saved to evals/results/")
    print("Next step: run run_eval.py to score V1 vs V2.")


if __name__ == "__main__":
    main()