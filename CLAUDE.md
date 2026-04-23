# AI Policy Copilot

## What this is

An AI-powered tool that helps organizations write, understand, and enforce
their internal AI usage policies. Users paste a policy draft or describe
their situation — the tool explains what's allowed, what's not, cites the
relevant policy section, and suggests safer alternatives.

## Who it's for

- HR and legal teams writing AI policies from scratch
- Employees who want to know if a specific AI use case is allowed
- Managers making decisions about AI tool adoption

## Core workflow

1. User inputs their company AI policy (or uses a default template)
2. User asks a specific question about an AI use case
3. System searches the policy, explains the ruling, cites the section
4. If not allowed — suggests a compliant alternative
5. Edge cases get flagged for human review

## Agent architecture

- research-agent — researches AI policy best practices and regulations
- policy-drafter — writes policy sections based on company context
- policy-reviewer — audits policy drafts for gaps and ambiguities
- compliance-checker — answers user questions against the policy

## Tech stack

- Python + Streamlit (frontend)
- Anthropic Claude API (reasoning)
- Playwright MCP (research)
- ChromaDB (policy vector storage)

## Deployment

- Streamlit Cloud
- GitHub: Nityaa2396/ai-policy-copilot

## Rules for Claude

- Always cite the specific policy section before answering
- Never give legal advice — always add disclaimer
- Flag edge cases clearly rather than guessing
- Keep explanations under 150 words
- Suggest alternatives when something is not allowed
