⚠️ This is a sample policy template for demonstration purposes only. Not legal advice. Review with qualified legal counsel before official use.

# Acme Corp AI Usage Policy

**Version:** 1.0
**Effective date:** 2026-01-01
**Owner:** Legal & Compliance
**Applies to:** All employees, contractors, and vendors performing work for Acme Corp

## 1. Purpose and Scope

### 1.1 Purpose
This policy defines how Acme Corp personnel may use artificial intelligence tools in the course of company work. It is intended to enable productive use of AI while protecting customer data, intellectual property, and the company's regulatory posture.

### 1.2 Scope
This policy applies to all AI-enabled tools accessed for company purposes, whether on company-owned or personal devices, and regardless of whether the tool is licensed by Acme Corp.

## 2. Approved AI Tools

### 2.1 Tier 1 — Generally approved
The following tools are approved for day-to-day use with non-confidential data:

- **ChatGPT** (OpenAI) — Team and Enterprise plans only. Personal free-tier accounts may not be used for company work.
- **Claude** (Anthropic) — Claude.ai Team plan and API access through approved integrations.
- **GitHub Copilot** — Business and Enterprise tiers, configured with organization-level content filtering and telemetry controls.

### 2.2 Tier 2 — Conditionally approved
Other AI tools may be used only after review by the AI Governance Committee. Submit requests through the IT Service Portal at least 10 business days before intended use.

### 2.3 Prohibited tools
Any AI tool not listed in 2.1 or approved under 2.2 is prohibited for company work. Personal free-tier consumer AI services are prohibited for any task involving company data.

## 3. Prohibited Uses

The following uses of AI tools are prohibited regardless of tool tier:

### 3.1 Legal documents
AI tools may not be used to generate, finalize, or provide legal advice on contracts, terms of service, privacy policies, regulatory filings, or litigation materials. Drafting assistance on internal memos is permitted only with review by Legal.

### 3.2 Medical advice
AI tools may not be used to generate medical, diagnostic, or clinical guidance for employees, customers, or any third party.

### 3.3 Personally identifiable information (PII)
Personally identifiable information — including names combined with government IDs, health data, financial account numbers, biometric data, or precise geolocation — may not be entered into any AI tool, including Tier 1 tools, unless explicitly approved under Section 4.

### 3.4 Automated decisions about people
AI tools may not be used to make or materially influence hiring, termination, compensation, promotion, performance management, credit, or benefits decisions without a documented human-in-the-loop review and Legal sign-off.

### 3.5 Deceptive content
AI tools may not be used to impersonate real individuals, generate content intended to mislead customers or regulators, or produce synthetic media of real people without their written consent.

## 4. Data Handling

### 4.1 Data classification
Acme data is classified as:

- **Public** — already released publicly
- **Internal** — non-sensitive internal information
- **Confidential** — business-sensitive (roadmaps, financials, non-public contracts)
- **Restricted** — customer data, PII, source code for core products, security material

### 4.2 What may be entered into AI tools

| Data class | Tier 1 tool | Tier 2 tool | Any other tool |
|---|---|---|---|
| Public | Allowed | Allowed | Not allowed |
| Internal | Allowed | Allowed with review | Not allowed |
| Confidential | Allowed only in Enterprise/Team plans with no-training settings confirmed | Requires Committee approval | Not allowed |
| Restricted | Not allowed | Not allowed | Not allowed |

### 4.3 No training on company data
All approved AI tools must be configured so that prompts and outputs are not used to train third-party models. Proof of configuration must be retained by IT.

### 4.4 No confidential data in public AI tools
Confidential or Restricted data must never be entered into consumer or free-tier AI services, shared chat links, or browser extensions that route data to unreviewed providers.

## 5. Content Guidelines

### 5.1 Human review required
No AI-generated content may be published externally, delivered to a customer, or merged into production code without documented review by a qualified human. "Review" means the reviewer understands the content and takes responsibility for its accuracy.

### 5.2 Disclosure
When AI has materially produced customer-facing content (marketing copy, support responses, reports delivered to clients), the customer must be informed in line with Acme's disclosure standard.

### 5.3 Accuracy and attribution
Employees are responsible for verifying factual claims in AI-generated content. AI outputs must not be cited as an authoritative source. Third-party content reproduced by an AI tool must be checked for licensing and attribution obligations before use.

### 5.4 Code generated by AI
Code produced by AI tools is subject to the same review, testing, and security standards as human-written code. License compatibility of any suggested snippets must be verified before merge.

## 6. Compliance and Logging

### 6.1 Logging requirement
All AI tool use for company work must be logged. For Tier 1 tools, IT maintains centralized logs via the enterprise admin console. For Tier 2 tools, the requesting team is responsible for maintaining a use log reviewed quarterly by Compliance.

### 6.2 Records retention
AI usage logs are retained for a minimum of 24 months, or longer where required by applicable law or contract.

### 6.3 Audit
The AI Governance Committee conducts an annual audit of AI usage across the company. Teams must cooperate with reasonable audit requests.

### 6.4 Incident reporting
Suspected policy violations, data leaks, or harmful AI outputs must be reported to security@acme.example within 24 hours of discovery.

## 7. Edge Cases

### 7.1 Personal use on company devices
Employees may use personal AI accounts on company devices for personal, non-work tasks during breaks, provided no company data is entered and the use does not violate Acme's acceptable-use policy. Personal accounts may not be used for any task related to company work, even drafting.

### 7.2 Client-facing AI
AI tools that interact directly with clients (chatbots, AI agents, automated email responders) require AI Governance Committee review before deployment. Such tools must:

- Clearly disclose that the client is interacting with AI
- Provide a path to reach a human
- Log all client interactions per Section 6
- Undergo quarterly bias and accuracy testing

### 7.3 Contractors and vendors
Contractors performing work for Acme are bound by this policy through their engagement agreements. Vendors using AI to deliver services to Acme must disclose such use and meet equivalent data-handling standards.

### 7.4 Personal devices (BYOD)
Employees using personal devices for company work must use only approved Tier 1 tools authenticated via Acme SSO. Unmanaged personal AI accounts on personal devices may not be used for company work.

### 7.5 Research and red-teaming
Security research, model evaluation, and red-team activities may require deviation from this policy. Such deviations require written pre-approval from the AI Governance Committee and Security.

### 7.6 Emergency exceptions
If strict adherence to this policy would prevent responding to a security incident or urgent customer obligation, employees should act in good faith to minimize harm and report the deviation to Compliance within 24 hours.

## 8. Enforcement

### 8.1 Consequences
Violations may result in disciplinary action up to and including termination, and may be reported to regulators or law enforcement where required.

### 8.2 Ownership
This policy is owned by Legal & Compliance and reviewed at least annually, or sooner when material regulatory or tooling changes occur.

### 8.3 Questions
Questions about this policy should be directed to aigovernance@acme.example.
