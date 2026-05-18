from __future__ import annotations

import re
from pathlib import Path

from app.schemas import ParsedIncident


SECTION_ALIASES = {
    "summary": "summary",
    "timeline": "timeline",
    "impact": "impact",
    "root cause": "root_cause",
    "resolution": "resolution",
    "follow-up actions": "follow_up_actions",
    "follow up actions": "follow_up_actions",
}

REQUIRED_SECTIONS = (
    "summary",
    "impact",
    "root_cause",
    "resolution",
)

HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def parse_incident_file(path: str | Path) -> ParsedIncident:
    incident_path = Path(path)
    if not incident_path.exists():
        raise FileNotFoundError(f"Incident file not found: {incident_path}")
    return parse_incident_markdown(incident_path.read_text(encoding="utf-8"))


def parse_incident_markdown(markdown: str) -> ParsedIncident:
    sections = _extract_sections(markdown)
    missing = [section for section in REQUIRED_SECTIONS if not sections.get(section)]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required incident section(s): {joined}")

    return ParsedIncident(
        summary=_as_text(sections["summary"]),
        timeline=_as_items(sections.get("timeline", [])),
        impact=_as_text(sections["impact"]),
        root_cause=_as_text(sections["root_cause"]),
        resolution=_as_text(sections["resolution"]),
        follow_up_actions=_as_items(sections.get("follow_up_actions", [])),
    )


def _extract_sections(markdown: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for raw_line in markdown.splitlines():
        heading_match = HEADING_RE.match(raw_line)
        if heading_match:
            normalized = _normalize_heading(heading_match.group(1))
            current = SECTION_ALIASES.get(normalized)
            if current is not None:
                sections.setdefault(current, [])
            continue

        if current is not None:
            sections[current].append(raw_line.rstrip())

    return {name: _trim_blank_lines(lines) for name, lines in sections.items()}


def _normalize_heading(value: str) -> str:
    return value.strip().strip(":").lower()


def _trim_blank_lines(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def _as_text(lines: list[str]) -> str:
    paragraphs: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(_strip_list_marker(stripped))

    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs).strip()


def _as_items(lines: list[str]) -> list[str]:
    items: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        items.append(_strip_list_marker(stripped))

    return items


def _strip_list_marker(value: str) -> str:
    return LIST_MARKER_RE.sub("", value, count=1).strip()
