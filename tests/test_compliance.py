"""Tests for policy loading, compliance decisions, and URL fetching."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.compliance_engine import (
    LEGAL_DISCLAIMER,
    NO_POLICY_DISCLAIMER,
    check_compliance,
    disclaimer_for,
)
from src.policy_loader import load_policy


def test_policy_loader(sample_policy):
    sections = load_policy(sample_policy)

    assert "Acme AI Usage Policy" in sections

    body = sections["Acme AI Usage Policy"]
    assert "Approved Tools" in body
    assert "Prohibited Uses" in body
    assert "ChatGPT Enterprise" in body
    assert "PII" in body


def test_compliance_allowed(sample_policy, mock_anthropic_factory):
    fake_client = mock_anthropic_factory(
        {
            "verdict": "allowed",
            "why": "Copilot Business is explicitly approved for code with human review.",
            "citation": "§ 2.2 GitHub Copilot",
            "safer_alternative": "",
            "needs_human_review": False,
        }
    )

    response = check_compliance(
        question="Can I use GitHub Copilot to write internal tooling?",
        policy_text=sample_policy,
        client=fake_client,
    )

    assert response.verdict == "allowed"
    assert "2.2" in response.citation
    assert response.safer_alternative == ""
    assert response.needs_human_review is False
    assert disclaimer_for(sample_policy) == LEGAL_DISCLAIMER


def test_compliance_not_allowed(sample_policy, mock_anthropic_factory):
    fake_client = mock_anthropic_factory(
        {
            "verdict": "not_allowed",
            "why": "Entering customer PII into any AI tool is prohibited.",
            "citation": "§ 3.1 Customer PII",
            "safer_alternative": "Redact or tokenize identifiers before sending the prompt.",
            "needs_human_review": True,
        }
    )

    response = check_compliance(
        question="Can I paste a customer's full name and SSN into Claude to summarize a case?",
        policy_text=sample_policy,
        client=fake_client,
    )

    assert response.verdict == "not_allowed"
    assert "3.1" in response.citation
    assert response.safer_alternative
    assert "redact" in response.safer_alternative.lower() or "token" in response.safer_alternative.lower()
    assert response.needs_human_review is True


def test_compliance_edge_case(sample_policy, mock_anthropic_factory):
    fake_client = mock_anthropic_factory(
        {
            "verdict": "needs_review",
            "why": "The policy requires human review of AI content but is silent on internal-only drafts.",
            "citation": "§ 4. Content Guidelines",
            "safer_alternative": "",
            "needs_human_review": True,
        }
    )

    response = check_compliance(
        question="Do internal brainstorming notes drafted with AI also need human review?",
        policy_text=sample_policy,
        client=fake_client,
    )

    assert response.verdict == "needs_review"
    assert response.safer_alternative == ""
    assert response.citation


def test_compliance_allowed_with_caution(sample_policy, mock_anthropic_factory):
    fake_client = mock_anthropic_factory(
        {
            "verdict": "allowed_with_caution",
            "why": "Drafting customer emails is permitted, but customer data must be redacted first.",
            "citation": "§ 3.1 Customer PII",
            "safer_alternative": "Paraphrase the scenario and strip any personal identifiers before prompting.",
            "needs_human_review": False,
        }
    )

    response = check_compliance(
        question="Can I use ChatGPT to draft a reply to a customer email?",
        policy_text=sample_policy,
        client=fake_client,
    )

    assert response.verdict == "allowed_with_caution"
    assert response.safer_alternative


def test_empty_policy(mock_anthropic_factory):
    fake_client = mock_anthropic_factory(
        {
            "verdict": "needs_review",
            "why": "No company policy was provided; defer to NIST AI RMF's human oversight guidance.",
            "citation": "General AI frameworks — no company policy loaded",
            "safer_alternative": "",
            "needs_human_review": True,
        }
    )

    response = check_compliance(
        question="Can I use ChatGPT for anything?",
        policy_text="",
        client=fake_client,
    )

    assert response.verdict == "needs_review"
    assert disclaimer_for("") == NO_POLICY_DISCLAIMER


def test_empty_policy_none_input(mock_anthropic_factory):
    fake_client = mock_anthropic_factory(
        {
            "verdict": "needs_review",
            "why": "Without a policy, defer to general frameworks.",
            "citation": "General AI frameworks — no company policy loaded",
            "safer_alternative": "",
            "needs_human_review": True,
        }
    )

    response = check_compliance(
        question="Any rules?", policy_text=None, client=fake_client
    )
    assert response.verdict == "needs_review"
    assert disclaimer_for(None) == NO_POLICY_DISCLAIMER


def test_url_fetch():
    from app import fetch_policy_from_url

    html = b"""
    <html>
      <head>
        <style>body { color: red; }</style>
        <script>console.log("ignore me");</script>
        <title>Acme Policy</title>
      </head>
      <body>
        <h1>Acme AI Policy</h1>
        <p>Employees must not enter customer PII into AI tools.</p>
      </body>
    </html>
    """

    mock_response = MagicMock()
    mock_response.text = html.decode("utf-8")
    mock_response.raise_for_status = MagicMock()

    with patch("app.requests.get", return_value=mock_response) as mock_get:
        text = fetch_policy_from_url("https://example.com/policy")

    mock_get.assert_called_once()
    assert "Acme AI Policy" in text
    assert "customer PII" in text
    assert "console.log" not in text
    assert "color: red" not in text


def test_url_fetch_raises_on_http_error():
    from app import fetch_policy_from_url

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = RuntimeError("404 Not Found")

    with patch("app.requests.get", return_value=mock_response):
        with pytest.raises(RuntimeError):
            fetch_policy_from_url("https://example.com/missing")
