"""PolicyCopilot — Streamlit frontend (native, minimal)."""

from __future__ import annotations

import base64
import os
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from src.compliance_engine import check_compliance, disclaimer_for
from src.policy_loader import chunk_by_heading, list_section_headings


load_dotenv()

DEFAULT_POLICY_PATH = Path(__file__).parent / "data" / "default_policy.md"

DRAFTER_MODEL = "claude-haiku-4-5-20251001"
DRAFTER_MAX_TOKENS = 800

INDUSTRY_OPTIONS = ["Technology", "Healthcare", "Finance", "Legal", "Education", "Retail", "Other"]
SIZE_OPTIONS = ["1-50", "51-200", "201-1000", "1000+"]
TOOL_OPTIONS = ["ChatGPT", "Claude", "GitHub Copilot", "Gemini", "Midjourney", "Other"]
CONCERN_OPTIONS = [
    "Data privacy", "Copyright/IP", "Accuracy/hallucinations",
    "Employee productivity misuse", "All of the above",
]

ROLE_OPTIONS = ["Sales", "HR", "Engineering", "Marketing", "Legal/Ops"]

ROLE_EXAMPLES: dict[str, list[str]] = {
    "Sales": [
        "Can I use AI to draft a client proposal?",
        "Can I summarize a competitor's website with AI?",
        "Can I use AI to personalize cold outreach emails?",
    ],
    "HR": [
        "Can HR use AI to summarize interview notes?",
        "Can I use AI to screen resumes?",
        "Can I paste employee feedback into an AI tool?",
    ],
    "Engineering": [
        "Can I paste production logs into ChatGPT?",
        "Can I use GitHub Copilot for client code?",
        "Can I let an AI agent run terminal commands?",
    ],
    "Marketing": [
        "Can I use AI to write social media posts?",
        "Can I use AI to generate images for campaigns?",
        "Can I use AI to analyze customer survey data?",
    ],
    "Legal/Ops": [
        "Can I use AI to draft a contract?",
        "Can I summarize legal documents with AI?",
        "Can I use AI for compliance research?",
    ],
}


# ----------------------------------------------------------------------
# Backend helpers
# ----------------------------------------------------------------------


class _HTMLTextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip == 0:
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", raw)).strip()


def fetch_policy_from_url(url: str) -> str:
    r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (PolicyCopilot)"})
    r.raise_for_status()
    p = _HTMLTextExtractor()
    p.feed(r.text)
    return p.text()


def generate_policy(industry: str, size: str, tools: list[str], concern: str) -> str:
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    tools_line = ", ".join(tools) if tools else "None specified"
    today = date.today().isoformat()
    prompt = (
        "Draft a realistic internal AI usage policy in Markdown for the following company:\n\n"
        f"- Industry: {industry}\n"
        f"- Headcount: {size}\n"
        f"- Tools currently in use: {tools_line}\n"
        f"- Primary AI concern: {concern}\n\n"
        'Use "Your Organization" as the company name throughout. '
        f'Use "{today}" as the effective date. Do NOT use bracketed placeholder text.\n\n'
        "Start directly with the first policy section. Use numbered sections with clear H2 headings. "
        "Cover approved tools, prohibited uses, data handling, content review, compliance/logging, "
        "and edge cases. Open with a one-line disclaimer that this is a generated draft, not legal advice."
    )
    msg = client.messages.create(
        model=DRAFTER_MODEL, max_tokens=DRAFTER_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            return block.text.strip()
    return ""


def _find_cited_section(citation: str, policy_text: str) -> str:
    sections = chunk_by_heading(policy_text)
    if not sections:
        return ""
    cleaned = citation.strip().lstrip("§").strip()
    for heading in list_section_headings(sections):
        if cleaned and cleaned.lower() in heading.lower():
            return sections[heading]
        if heading.lower() in cleaned.lower():
            return sections[heading]
    m = re.search(r"(\d+(?:\.\d+)*)", cleaned)
    if m:
        n = m.group(1)
        for heading in list_section_headings(sections):
            if n in heading:
                return sections[heading]
    return ""


# ----------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------


def init_state() -> None:
    defaults = {
        "policy_text": "",
        "policy_label": "",
        "question": "",
        "result": None,
        "selected_role": "Sales",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if "history" not in st.session_state:
        st.session_state.history = []


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------


def on_policy_type_change() -> None:
    st.session_state.result = None
    st.session_state.policy_text = None
    st.session_state.policy_source = None
    st.session_state.question = ""
    st.session_state.question_input = ""
    if "selected_role" in st.session_state:
        st.session_state.selected_role = "Sales"


def render_policy_step() -> None:
    st.subheader("Step 1 — Load your policy")

    policy_input_type = st.radio(
        "Policy source",
        ["Paste", "Upload", "URL", "Generate"],
        horizontal=True,
        key="policy_input_type",
        on_change=on_policy_type_change,
    )

    if policy_input_type == "Paste":
        text = st.text_area(
            "Paste policy text",
            placeholder="Paste your organization's AI usage policy here...",
            height=180,
            key="paste_input",
        )
        if st.button("Use this policy", key="use_paste", type="primary"):
            if text.strip():
                st.session_state.policy_text = text
                st.session_state.policy_label = "Pasted policy"
                st.session_state.policy_source = "Paste"
                st.session_state.result = None
                st.rerun()
            else:
                st.warning("Paste some text first.")

    elif policy_input_type == "Upload":
        uploaded = st.file_uploader("Upload a .md or .txt policy", type=["md", "txt"])
        if st.button("Use this policy", key="use_upload", type="primary"):
            if uploaded is not None:
                st.session_state.policy_text = uploaded.read().decode("utf-8", errors="replace")
                st.session_state.policy_label = f"Uploaded: {uploaded.name}"
                st.session_state.policy_source = "Upload"
                st.session_state.result = None
                st.rerun()
            else:
                st.warning("Choose a file first.")

    elif policy_input_type == "URL":
        url = st.text_input("Policy URL", placeholder="https://company.com/ai-policy", key="url_input")
        if st.button("Fetch from URL", key="fetch_url"):
            if url.strip():
                with st.spinner("Fetching..."):
                    try:
                        fetched = fetch_policy_from_url(url.strip())
                        if fetched:
                            host = urlparse(url.strip()).netloc or url.strip()
                            st.session_state.policy_text = fetched
                            st.session_state.policy_label = f"URL: {host}"
                            st.session_state.policy_source = "URL"
                            st.session_state.result = None
                            st.rerun()
                        else:
                            st.error("No readable content at that URL.")
                    except Exception as exc:
                        st.error(f"Could not fetch: {exc}")
            else:
                st.warning("Enter a URL first.")

    elif policy_input_type == "Generate":
        industry = st.selectbox("Industry", INDUSTRY_OPTIONS, key="gen_industry")
        size = st.selectbox("Headcount", SIZE_OPTIONS, key="gen_size")
        tools = st.multiselect("Tools in use", TOOL_OPTIONS, key="gen_tools")
        concern = st.selectbox("Biggest concern", CONCERN_OPTIONS, key="gen_concern")
        if st.button("Generate My Policy", key="gen_btn"):
            with st.spinner("✍️ Drafting your policy..."):
                try:
                    drafted = generate_policy(industry, size, tools, concern)
                    if drafted:
                        st.session_state.policy_text = drafted
                        st.session_state.policy_label = "Generated policy"
                        st.session_state.policy_source = "Generate"
                        st.session_state.result = None
                        st.rerun()
                except Exception as exc:
                    st.error(f"Policy generation failed: {exc}")

    if (
        st.session_state.policy_text
        and st.session_state.get("policy_source") == policy_input_type
    ):
        st.success("✅ Policy loaded")


def on_role_change() -> None:
    st.session_state.result = None
    st.session_state.question = ""
    st.session_state.question_input = ""


def render_question_step() -> bool:
    st.subheader("Step 2 — Ask a question")

    st.radio(
        "Your role",
        ROLE_OPTIONS,
        horizontal=True,
        key="selected_role",
        on_change=on_role_change,
    )

    def _on_question_change() -> None:
        st.session_state.result = None

    question = st.text_area(
        "What do you want to do?",
        value=st.session_state.get("question", ""),
        placeholder="e.g. Can I paste customer emails into ChatGPT?",
        height=110,
        key="question_input",
        on_change=_on_question_change,
    )
    st.session_state.question = question

    role = st.session_state.get("selected_role", "Sales")
    examples = ROLE_EXAMPLES.get(role, [])
    if examples:
        st.caption("Or try an example:")
        cols = st.columns(len(examples))
        for col, example in zip(cols, examples):
            with col:
                if st.button(example, key=f"ex_{role}_{example[:20]}", use_container_width=True):
                    st.session_state.question = example
                    st.rerun()

    return st.button("Get Decision →", type="primary", key="get_decision")


def render_decision_step() -> None:
    result = st.session_state.result
    if result is None:
        return

    st.subheader("Step 3 — Decision")

    verdict_map = {
        "allowed": ("success", "✓ Allowed"),
        "allowed_with_caution": ("warning", "⚠ Allowed with caution"),
        "not_allowed": ("error", "✕ Not allowed"),
        "needs_review": ("info", "↗ Needs review"),
    }
    style, label = verdict_map.get(result.verdict, ("info", result.verdict))
    getattr(st, style)(label)

    if result.why:
        st.write(result.why)

    if result.safer_alternative:
        st.info(f"**Safer alternative:** {result.safer_alternative}")

    if result.needs_human_review:
        st.warning("This request should be confirmed with HR, Legal, or Security.")

    if result.citation:
        st.caption(f"Citation: {result.citation}")
        quote = _find_cited_section(result.citation, st.session_state.policy_text)
        if quote:
            with st.expander("Show the cited section"):
                st.markdown(quote)

    st.caption(disclaimer_for(st.session_state.policy_text or None))

    if st.button("Ask a new question", key="new_question"):
        st.session_state.result = None
        st.session_state.question = ""
        st.rerun()


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="PolicyCopilot", page_icon="🛡️")

    def get_base64_image(image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    img_path = os.path.join(os.path.dirname(__file__), "static", "policy-bg.png")
    if os.path.exists(img_path):
        bg_image = get_base64_image(img_path)
        bg_css = f"url('data:image/png;base64,{bg_image}')"
    else:
        bg_css = "none"

    st.markdown(
        f"""<style>
#MainMenu, footer, header {{visibility: hidden;}}
[data-testid="stAppViewContainer"] {{
    background-image: {bg_css};
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
[data-testid="stMain"] {{
    background: transparent !important;
}}
.block-container {{
    background: rgba(255, 255, 255, 0.92);
    border-radius: 16px;
    padding: 2rem !important;
    margin-top: 1rem;
}}
.stMarkdown, .stText, label, p, h1, h2, h3 {{ color: #111827 !important; }}
.stTextArea textarea, .stTextInput input {{ background: white !important; color: #111827 !important; }}
div.stButton > button {{
    color: #111827 !important;
    background-color: white !important;
    border: 1px solid #d1d5db !important;
}}
div.stButton > button:hover {{
    color: #111827 !important;
    background-color: #f9fafb !important;
}}
div[data-testid="stBaseButton-primaryFormSubmit"],
div[data-testid="stBaseButton-primary"] {{
    background-color: #111827 !important;
    color: white !important;
    border: none !important;
}}
div[data-testid="stBaseButton-primary"] p,
div[data-testid="stBaseButton-primaryFormSubmit"] p {{
    color: white !important;
}}
</style>""",
        unsafe_allow_html=True,
    )

    init_state()

    st.title("🛡️ PolicyCopilot")
    st.caption("The AI usage decision assistant · Not legal advice")
    st.divider()

    render_policy_step()

    st.divider()
    submitted = render_question_step()

    if submitted:
        if not st.session_state.policy_text:
            st.warning("Load a policy first.")
        elif not st.session_state.question.strip():
            st.warning("Type a question first.")
        else:
            with st.spinner("Thinking through your policy..."):
                try:
                    result = check_compliance(
                        question=st.session_state.question,
                        policy_text=st.session_state.policy_text,
                    )
                    st.session_state.result = result
                    st.session_state.history.append({
                        "question": st.session_state.get("question_input", ""),
                        "role": st.session_state.get("selected_role", ""),
                        "verdict": result.verdict,
                    })
                    st.session_state.history = st.session_state.history[-5:]
                    st.rerun()
                except Exception as exc:
                    st.error(f"Decision failed: {exc}")

    st.divider()
    render_decision_step()

    if st.session_state.history:
        st.divider()
        st.subheader("Recent questions")
        for i, item in enumerate(reversed(st.session_state.history)):
            verdict_icon = {
                "allowed": "✓",
                "allowed_with_caution": "⚠",
                "not_allowed": "✕",
                "needs_review": "↗",
            }.get(item["verdict"], "?")
            if st.button(
                f"{verdict_icon} [{item['role']}] {item['question'][:60]}",
                key=f"hist_{i}_{item['question'][:15]}",
            ):
                st.session_state.question_input = item["question"]
                st.session_state.selected_role = item["role"]
                st.rerun()


if __name__ == "__main__":
    main()
