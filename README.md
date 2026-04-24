# PolicyCopilot

The AI usage decision assistant for employees.

## The problem

Employees want to use AI tools. But they often don't know what's allowed, what's risky, or which workflows are safer. This creates confusion, inconsistent usage, and compliance risk.

## What PolicyCopilot does

PolicyCopilot is an AI usage decision assistant. Bring your company's AI policy, ask real employee questions, get clear decisions with citations and safer alternatives.

## Sample questions

- Can I paste client emails into ChatGPT?
- Can HR use AI to summarize interview notes?
- Can engineering paste logs into an external AI tool?
- Can sales use AI to draft a client proposal?

## Features

- Load your policy by paste, file upload, or live URL fetch
- Generate a starter policy by answering four questions about your organization
- Structured decisions: `allowed`, `allowed with caution`, `not allowed`, or `needs review`
- Every decision includes a citation to the exact policy section
- Safer alternatives surfaced when the use case isn't allowed or needs care
- Edge cases flagged with a "check with HR/Legal" signal

## Tech stack

- Python + Streamlit
- Anthropic Claude API
- Requests for live URL fetching
- pytest for automated testing

## How to run locally

1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Add `ANTHROPIC_API_KEY` to `.env`
4. Run: `streamlit run app.py`

## Test results

Run with: `pytest tests/ -v`

## Deployment

Live at: https://ai-policy-copilot.streamlit.app/

## Implementation notes

Under the hood, PolicyCopilot is organized as a small set of agents:

- `policy-drafter` — drafts a starter policy from org context
- `policy-reviewer` — audits drafts for gaps, ambiguities, and edge cases
- `compliance-checker` — answers employee questions against the loaded policy with citations

Definitions live in `.claude/agents/`. The runtime uses the Anthropic SDK directly from [src/compliance_engine.py](src/compliance_engine.py) and [app.py](app.py); the agent files are used by Claude Code when driving this repo interactively.

## Disclaimer

Not legal advice. Always consult qualified legal counsel before adopting or enforcing any AI policy.
