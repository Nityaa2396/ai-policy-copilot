"""Load and chunk AI usage policies into sections keyed by heading."""

from __future__ import annotations

import re
from pathlib import Path


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def load_policy(source: str | Path) -> dict[str, str]:
    """Load a policy from a file path or raw text and return sections keyed by heading.

    Accepts either a filesystem path to a Markdown file or the policy text itself.
    Returns a dictionary mapping the section heading (without `#` markers) to the
    Markdown content of that section, including any nested subsections.

    Text that appears before the first heading is stored under the key `__preamble__`.
    """
    text = _read_source(source)
    return chunk_by_heading(text)


def _read_source(source: str | Path) -> str:
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8")

    if source.lstrip().startswith("#") or "\n" in source:
        return source

    candidate = Path(source)
    if len(source) < 4096 and candidate.exists() and candidate.is_file():
        return candidate.read_text(encoding="utf-8")

    return source


def chunk_by_heading(text: str) -> dict[str, str]:
    """Split Markdown text into a dict keyed by heading text.

    Headings at any level (`#` through `######`) start a new section. A section
    ends where the next heading of the same or higher level begins. Nested
    subsections are kept inside their parent section's body.
    """
    sections: dict[str, str] = {}
    matches = list(HEADING_PATTERN.finditer(text))

    if not matches:
        stripped = text.strip()
        if stripped:
            sections["__preamble__"] = stripped
        return sections

    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections["__preamble__"] = preamble

    top_level = min(len(m.group(1)) for m in matches)

    for i, match in enumerate(matches):
        level = len(match.group(1))
        if level != top_level:
            continue

        heading = match.group(2).strip()
        body_start = match.end()

        body_end = len(text)
        for later in matches[i + 1 :]:
            if len(later.group(1)) <= top_level:
                body_end = later.start()
                break

        section_body = text[match.start() : body_end].rstrip()
        sections[heading] = section_body

    return sections


def list_section_headings(sections: dict[str, str]) -> list[str]:
    """Return the ordered list of top-level headings, excluding the preamble."""
    return [key for key in sections if key != "__preamble__"]
