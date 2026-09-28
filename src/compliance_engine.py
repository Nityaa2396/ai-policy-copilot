"""Answer user questions about AI use cases against a loaded company policy."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Literal
import hashlib
from src.vector_store import index_policy, search_chunks, policy_is_indexed

from anthropic import Anthropic


Verdict = Literal["allowed", "allowed_with_caution", "not_allowed", "needs_review"]

MODEL = "claude-sonnet-4-6"

LEGAL_DISCLAIMER = (
    "This is not legal advice. For binding guidance, consult your legal or "
    "compliance team before making decisions."
)

NO_POLICY_DISCLAIMER = (
    "⚠️ No company policy loaded. Responses are based on general AI frameworks "
    "(EU AI Act, NIST AI RMF, ISO 42001) only — not your organization's official "
    "policy. Consult your legal or compliance team before making decisions."
)

SYSTEM_PROMPT = """You are a decision assistant for an internal AI usage policy.

You receive a user question describing an AI use case and the full policy text. You return a structured decision.

Rules you must follow:
- Ground every decision in the provided policy text. Never invent clauses or section numbers.
- Cite the exact section heading and, if present, the section number (e.g., "§ 3.3 Personally identifiable information (PII)").
- Verdict must be one of:
  - "allowed" — the policy clearly permits the use and any stated conditions are already satisfied.
  - "allowed_with_caution" — permitted but the user should follow a condition or mitigate a stated risk (e.g., disclosure, redaction, approved tool tier).
  - "not_allowed" — the policy clearly prohibits it, or a hard precondition is unmet.
  - "needs_review" — the policy is silent, ambiguous, contradictory, or the facts are insufficient to decide.
- "why" must be ≤ 100 words, plain language, no hedging.
- "safer_alternative" must be non-empty when verdict is "not_allowed" or "allowed_with_caution"; otherwise use an empty string.
- "needs_human_review" is a boolean. Set it to true when the use case involves regulated data, legal/financial risk, a contested clause, or anything a reasonable compliance owner should double-check — even if the verdict is "allowed".
- If no policy text was supplied, reason from general AI frameworks (EU AI Act, NIST AI RMF, ISO 42001). Set citation to "General AI frameworks — no company policy loaded".

Output MUST be a single JSON object with exactly these keys and no others:
  "verdict": "allowed" | "allowed_with_caution" | "not_allowed" | "needs_review"
  "why": string (≤100 words)
  "citation": string
  "safer_alternative": string
  "needs_human_review": boolean

Do not include any text outside the JSON object."""


@dataclass
class ComplianceResponse:
    verdict: Verdict
    why: str
    citation: str
    safer_alternative: str
    needs_human_review: bool

    def to_dict(self) -> dict:
        return asdict(self)

def _classify_question(question: str, client: Anthropic) -> int:
    """
    Classify question complexity to determine how many chunks to retrieve.
    Returns top_k: 1 for direct lookup, 2 for inference, 3 for edge cases.
    """
    response = client.messages.create(
        model=MODEL,
        max_tokens=10,
        system="Classify this compliance question. Reply with ONLY a single digit: 1 if the answer is likely in one policy section, 2 if it requires combining multiple sections, 3 if it is ambiguous or an edge case.",
        messages=[{"role": "user", "content": question}],
    )
    for block in response.content:
        if getattr(block, "type", None) == "text":
            digit = block.text.strip()
            if digit in ("1", "2", "3"):
                return int(digit)
    return 2  # default to 2 if classification fails

def check_compliance(
    question: str,
    policy_text: str | None,
    *,
    client: Anthropic | None = None,
) -> ComplianceResponse:
    """Return a structured decision for a user AI-use question against the supplied policy.

    V2: Uses Qdrant vector search to find relevant chunks instead of
    sending the full policy to Claude on every question.
    """
    client = client or Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    has_policy = bool(policy_text and policy_text.strip())

    # V2: use vector search if policy is available
    if has_policy:
        # generate a stable ID for this policy
        policy_id = hashlib.md5(policy_text.encode()).hexdigest()[:16]

        # index policy in Qdrant if not already indexed
        if not policy_is_indexed(policy_id):
            index_policy(policy_text, policy_id)

        # retrieve only relevant chunks
        top_k = _classify_question(question, client)
        relevant_chunks = search_chunks(question, policy_id, top_k=top_k)

        if relevant_chunks:
            # use only relevant chunks instead of full policy
            context = "\n\n---\n\n".join(relevant_chunks)
        else:
            # fallback to full policy if search returns nothing
            context = policy_text

        user_content = _build_user_message(question, context, has_policy)
    else:
        user_content = _build_user_message(question, policy_text, has_policy)

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = _extract_text(message)
    payload = _parse_json(raw)

    verdict = _normalize_verdict(payload.get("verdict", "needs_review"))
    citation = str(payload.get("citation", "")).strip() or "No citation returned"
    why = str(payload.get("why", "")).strip()
    safer_alternative = str(payload.get("safer_alternative", "")).strip()
    if verdict not in ("not_allowed", "allowed_with_caution"):
        safer_alternative = ""
    needs_human_review = bool(payload.get("needs_human_review", False))

    return ComplianceResponse(
        verdict=verdict,
        why=why,
        citation=citation,
        safer_alternative=safer_alternative,
        needs_human_review=needs_human_review,
    )

def disclaimer_for(policy_text: str | None) -> str:
    """Return the disclaimer appropriate for whether a policy is loaded."""
    if policy_text and policy_text.strip():
        return LEGAL_DISCLAIMER
    return NO_POLICY_DISCLAIMER


def _build_user_message(question: str, policy_text: str | None, has_policy: bool) -> str:
    if has_policy:
        return (
            f"<policy>\n{policy_text.strip()}\n</policy>\n\n"
            f"<question>\n{question.strip()}\n</question>\n\n"
            "Return the JSON object described in the system prompt."
        )
    return (
        "<policy>\nNo company policy was provided. Reason from the EU AI Act, "
        "NIST AI RMF, and ISO 42001. Set citation to "
        '"General AI frameworks — no company policy loaded".\n</policy>\n\n'
        f"<question>\n{question.strip()}\n</question>\n\n"
        "Return the JSON object described in the system prompt."
    )


def _extract_text(message) -> str:
    for block in message.content:
        if getattr(block, "type", None) == "text":
            return block.text
    raise ValueError("Claude response contained no text block")


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in model output: {raw!r}")

    return json.loads(raw[start : end + 1])


def _normalize_verdict(value: str) -> Verdict:
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in ("allowed", "allowed_with_caution", "not_allowed", "needs_review"):
        return normalized  # type: ignore[return-value]
    legacy = {
        "edge_case": "needs_review",
        "edge": "needs_review",
        "unclear": "needs_review",
        "ambiguous": "needs_review",
        "caution": "allowed_with_caution",
        "conditional": "allowed_with_caution",
        "prohibited": "not_allowed",
    }
    return legacy.get(normalized, "needs_review")
