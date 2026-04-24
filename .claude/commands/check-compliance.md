---
description: Ask a compliance question against the loaded company AI policy — returns a ruling, citation, and (if needed) a compliant alternative.
argument-hint: <your question about an AI use case>
---

You are handling a `/check-compliance` request.

## The user's question

$ARGUMENTS

## What to do

1. Locate the company AI policy for this session. Check, in order:
   - A policy file referenced earlier in the conversation
   - `data/policy.md`, `data/policy.txt`, or any `*.md` / `*.pdf` under `data/`
   - The default template, if one exists in the repo
   If no policy is loaded, stop and ask the user to paste or point to their policy before proceeding.

2. Delegate the ruling to the `compliance-checker` agent. Pass it:
   - The user's question (verbatim from `$ARGUMENTS`)
   - The policy text (or the path if the agent can read it directly)
   - Any relevant context already shared in this conversation (e.g., the user's role, data classification, tool in use)

3. Return the agent's response to the user exactly as structured:
   - **Ruling** (`ALLOWED` / `NOT ALLOWED` / `NEEDS REVIEW`)
   - **Citation** (section number and heading)
   - **Explanation** (≤ 150 words)
   - **Alternative** (only if `NOT ALLOWED`)
   - **Disclaimer**

4. If the ruling is `NEEDS REVIEW`, make the next step concrete: tell the user which clarifying fact would change the ruling, or which internal contact should resolve it.

## Constraints

- Do not answer the compliance question yourself — always route through the `compliance-checker` agent so the output format stays consistent
- Never fabricate a citation. If the agent returns `NEEDS REVIEW` because retrieval failed, surface that honestly
- Never strip the legal-advice disclaimer from the response
