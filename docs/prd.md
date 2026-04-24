# AI Policy Copilot — Product Requirements Document

## 1. Overview

AI Policy Copilot is an AI-powered assistant that helps organizations author, understand, and enforce their internal AI usage policies. Users can paste a policy draft or describe a situation, and the tool will explain what is allowed, what is not, cite the relevant policy section, and suggest safer alternatives when a use case is disallowed.

## 2. Problem Statement

Organizations are rapidly adopting generative AI tools but lack clear, accessible, and enforceable policies governing their use. HR, legal, and compliance teams struggle to:

- Write comprehensive AI policies that anticipate real employee use cases
- Communicate policies in a way employees actually understand
- Answer the long tail of "can I use AI for X?" questions consistently
- Keep policies aligned with evolving regulations (EU AI Act, NIST AI RMF, state laws)

Employees, meanwhile, are left guessing — leading to either over-cautious under-adoption or risky misuse.

## 3. Target Users

| Persona | Primary Need |
|---|---|
| HR / Legal policy author | Draft a defensible, comprehensive AI policy from scratch or from a template |
| Employee / individual contributor | Get a quick, trustworthy answer on whether a specific AI use is allowed |
| People manager / team lead | Make adoption decisions for their team and onboard reports |
| Compliance / risk officer | Audit policy drafts for gaps, ambiguities, and regulatory coverage |

## 4. Goals and Non-Goals

### Goals
- Reduce time to produce a v1 internal AI policy from weeks to under an hour
- Answer ≥80% of employee AI-use questions without human escalation
- Always cite the specific policy clause backing every ruling
- Surface edge cases clearly rather than fabricating rulings

### Non-Goals
- Providing legal advice (tool must always include a disclaimer)
- Replacing human review for high-risk decisions
- Policy enforcement at the system/technical control level (e.g., DLP integration) in v1
- Multi-tenant SaaS with org accounts in v1 — single-policy sessions only

## 5. Core Workflows

### 5.1 Draft a policy
1. User provides company context (industry, size, regulatory regime, risk tolerance)
2. `policy-drafter` agent generates section drafts (acceptable use, data handling, tool approval, etc.)
3. `policy-reviewer` agent audits the draft and flags gaps / ambiguities
4. User iterates; final policy is stored in ChromaDB for later querying

### 5.2 Check compliance for a specific use case
1. User loads or pastes a policy (or uses the default template)
2. User asks a question (e.g., "Can I use ChatGPT to summarize a customer support ticket?")
3. `compliance-checker` retrieves relevant policy sections from ChromaDB
4. System returns: ruling (allowed / not allowed / needs review), the citation, the reasoning, and — if disallowed — a suggested alternative
5. Edge cases are flagged with a "needs human review" marker

### 5.3 Research best practices
1. User asks for guidance on a policy area (e.g., "how do peer companies handle customer data in AI tools?")
2. `research-agent` pulls from external sources via Playwright MCP and summarizes

## 6. Agent Architecture

| Agent | Responsibility |
|---|---|
| `research-agent` | Researches AI policy best practices, regulations, and peer benchmarks |
| `policy-drafter` | Writes policy sections tailored to company context and industry |
| `policy-reviewer` | Audits drafts for gaps, ambiguities, and missing edge cases |
| `compliance-checker` | Answers user questions against the loaded policy with citations |

## 7. Functional Requirements

- **FR-1** Accept policy input via paste, file upload (PDF, DOCX, MD), or default template
- **FR-2** Chunk and embed the policy into ChromaDB for semantic retrieval
- **FR-3** Every answer must cite the section heading or paragraph number of the source clause
- **FR-4** Every answer must include a "not legal advice" disclaimer
- **FR-5** When a use case is disallowed, the tool must propose at least one compliant alternative
- **FR-6** Uncertain or contradictory policy situations must be flagged `NEEDS_REVIEW` rather than guessed
- **FR-7** Explanations returned to end users must be ≤150 words
- **FR-8** Support exporting the final drafted policy as Markdown and PDF

## 8. Non-Functional Requirements

- **Latency** — compliance checks return in under 10 seconds at p95
- **Privacy** — no pasted policy content is logged or retained beyond the session
- **Transparency** — every ruling shows the retrieved chunks used to justify it
- **Accessibility** — Streamlit UI meets WCAG AA color contrast

## 9. Tech Stack

- **Frontend**: Streamlit
- **Language**: Python 3.11+
- **Reasoning**: Anthropic Claude API (Sonnet for agents, Opus for hard edge cases)
- **Vector store**: ChromaDB (local persistence)
- **Research**: Playwright MCP
- **Deployment**: Streamlit Cloud
- **Source**: GitHub — `Nityaa2396/ai-policy-copilot`

## 10. Success Metrics

| Metric | Target |
|---|---|
| Time to v1 policy draft | < 60 minutes |
| Compliance questions answered without escalation | ≥ 80% |
| Citation accuracy (ruling matches cited clause) | ≥ 95% |
| User-reported "explanation was clear" | ≥ 4.2 / 5 |
| p95 compliance-check latency | < 10 seconds |

## 11. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Hallucinated policy rulings | Require retrieval + citation; flag low-retrieval-confidence as `NEEDS_REVIEW` |
| Misinterpreted as legal advice | Mandatory disclaimer on every response |
| Policy drift from regulations | `research-agent` periodically surfaces regulatory updates |
| Over-broad refusals frustrate users | `compliance-checker` must propose an alternative when refusing |

## 12. Milestones

1. **M1 — Core compliance check** — load policy, answer questions with citations
2. **M2 — Drafting loop** — `policy-drafter` + `policy-reviewer` produce a v1 policy
3. **M3 — Research integration** — `research-agent` pulls external benchmarks
4. **M4 — Export and polish** — Markdown / PDF export, UI refinement, Streamlit Cloud deploy

## 13. Open Questions

- Which jurisdictions' regulations should the default template cover first (US federal, EU AI Act, CA, NY)?
- Should draft policies be versioned in Git or stored only in ChromaDB?
- How should the tool handle conflicts between company policy and applicable law?
