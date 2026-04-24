"""Shared fixtures for the compliance test suite."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SAMPLE_POLICY = """# Acme AI Usage Policy

## 1. Purpose

This policy defines acceptable AI use at Acme.

## 2. Approved Tools

### 2.1 Tier 1
ChatGPT Enterprise and Claude Team are approved for day-to-day work with non-confidential data.

### 2.2 GitHub Copilot
GitHub Copilot Business is approved for code generation with human review.

## 3. Prohibited Uses

### 3.1 Customer PII
Customer personally identifiable information (PII) may not be entered into any AI tool under any circumstances.

### 3.2 Legal Documents
AI tools may not be used to generate or finalize legal contracts.

## 4. Content Guidelines

All AI-generated content must be reviewed by a human before it is sent to customers or published.
"""


@pytest.fixture
def sample_policy() -> str:
    """A realistic policy with numbered sections and subsections."""
    return SAMPLE_POLICY


def build_mock_anthropic_client(payload: dict) -> SimpleNamespace:
    """Return a fake Anthropic client whose messages.create returns `payload` as JSON text."""
    text_block = SimpleNamespace(type="text", text=json.dumps(payload))
    message = SimpleNamespace(content=[text_block])

    class _Messages:
        def create(self, **_kwargs):
            return message

    return SimpleNamespace(messages=_Messages())


@pytest.fixture
def mock_anthropic_factory():
    """Hand tests a builder so each one can stage its own JSON payload."""
    return build_mock_anthropic_client
