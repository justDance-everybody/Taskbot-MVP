"""Acceptance contract — issue #12 §4.

Tasks created via N1 embed a YAML block in their GitHub issue body:

```yaml
acceptance:
  ci_required: ["test", "lint", "typecheck"]
  coverage_min: 80
  custom_commands:
    - "pytest tests/integration/test_xxx.py"
  forbid_files: [".env", "*.pem"]
  max_pr_lines: 2000
```

This module parses that block out and returns a typed contract that
downstream verification (ai_review, revision) consults.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Match a fenced YAML block whose top-level key is `acceptance:` (with or
# without leading whitespace inside the fence).
_FENCE_RE = re.compile(
    r"```ya?ml\s*\n(?P<body>.+?\n)```",
    re.DOTALL | re.IGNORECASE,
)


@dataclass
class AcceptanceContract:
    ci_required: list[str] = field(default_factory=list)
    coverage_min: int = 0
    custom_commands: list[str] = field(default_factory=list)
    forbid_files: list[str] = field(default_factory=list)
    max_pr_lines: int = 0

    @property
    def is_default(self) -> bool:
        """No real contract → conservative defaults (no requirements)."""
        return (
            not self.ci_required
            and self.coverage_min == 0
            and not self.custom_commands
            and not self.forbid_files
            and self.max_pr_lines == 0
        )


def parse_acceptance_yaml(body: str) -> AcceptanceContract:
    """Extract the ``acceptance:`` YAML block from a GitHub issue body.

    Returns the parsed contract; on missing block / parse error, returns
    an empty default contract (caller decides how to handle).

    PyYAML is intentionally optional — if not installed we fall back to a
    minimal hand-rolled parser that handles the documented shape.
    """
    if not body:
        return AcceptanceContract()
    match = _FENCE_RE.search(body)
    if not match:
        logger.debug("acceptance: no YAML fence found")
        return AcceptanceContract()
    yaml_text = match.group("body")
    data = _load_yaml(yaml_text)
    if not isinstance(data, dict):
        return AcceptanceContract()
    payload = data.get("acceptance") or data
    if not isinstance(payload, dict):
        return AcceptanceContract()

    return AcceptanceContract(
        ci_required=_as_list(payload.get("ci_required")),
        coverage_min=_as_int(payload.get("coverage_min")),
        custom_commands=_as_list(payload.get("custom_commands")),
        forbid_files=_as_list(payload.get("forbid_files")),
        max_pr_lines=_as_int(payload.get("max_pr_lines")),
    )


def _load_yaml(text: str) -> Optional[dict]:
    """Parse YAML; prefer PyYAML when available."""
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ImportError:
        logger.debug("acceptance: PyYAML missing; using fallback parser")
        return _fallback_parse(text)
    except Exception as exc:
        logger.warning("acceptance: PyYAML parse error: %s", exc)
        return None


def _fallback_parse(text: str) -> dict:
    """Minimal hand-rolled YAML for the documented schema only.

    Handles:
    - top-level keys: ``key: value``
    - nested ``acceptance:`` block via 2-space indent
    - inline lists ``[a, b]`` and block lists ``- a``
    - integer auto-coerce
    """
    out: dict = {}
    cur: dict = out
    section_indent = 0
    section_key: Optional[str] = None
    list_buffer: Optional[list] = None
    list_for_key: Optional[str] = None

    def _flush_list():
        nonlocal list_buffer, list_for_key
        if list_buffer is not None and list_for_key is not None:
            cur[list_for_key] = list_buffer
        list_buffer = None
        list_for_key = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())

        if line.lstrip().startswith("- "):
            if list_buffer is None:
                continue
            list_buffer.append(_strip_value(line.lstrip()[2:]))
            continue

        # Non-list line — flush any pending list
        _flush_list()

        if indent == 0:
            # New top-level key
            cur = out
            section_indent = 0
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if not value:
                    cur[key] = {}
                    section_key = key
                    section_indent = indent
                    cur = cur[key]
                else:
                    out[key] = _coerce(value)
        elif indent > section_indent:
            if ":" in line:
                key, _, value = line.lstrip().partition(":")
                key = key.strip()
                value = value.strip()
                if not value:
                    list_buffer = []
                    list_for_key = key
                else:
                    cur[key] = _coerce(value)
        elif indent <= section_indent:
            cur = out
            section_indent = 0
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if value:
                    out[key] = _coerce(value)
                else:
                    cur[key] = {}
                    section_key = key
                    cur = cur[key]
                    section_indent = indent

    _flush_list()
    return out


_INLINE_LIST_RE = re.compile(r"^\[(.*)\]$")


def _coerce(value: str):
    value = value.strip().strip("\"'")
    m = _INLINE_LIST_RE.match(value)
    if m:
        items = [s.strip().strip("\"'") for s in m.group(1).split(",") if s.strip()]
        return [_coerce_scalar(i) for i in items]
    return _coerce_scalar(value)


def _coerce_scalar(value: str):
    if value.isdigit():
        return int(value)
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value


def _strip_value(value: str):
    return _coerce_scalar(value.strip().strip("\"'"))


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _as_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
