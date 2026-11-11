"""Check active Codex Skill front matter and report missing safety markers."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def is_skipped(path: Path) -> bool:
    return any(
        part in {".git", ".codex-tmp", ".research"}
        or part.startswith("90_")
        or part.startswith("99_")
        or "系统演化档案" in part
        for part in path.parts
    )


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    skills = [p for p in ROOT.rglob("SKILL.md") if not is_skipped(p)]
    if not skills:
        print("NO_ACTIVE_SKILLS")
        return 1
    aliases = {
        "输入": ("输入", "input", "source"),
        "输出": ("输出", "output", "return"),
        "缺失": ("缺失", "missing", "unknown"),
        "停止": ("停止", "stop", "must not", "不得"),
    }
    for path in sorted(skills):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        if not text.startswith("---\n"):
            errors.append(f"{rel}: missing YAML front matter")
            continue
        closing = text.find("\n---", 4)
        front = text[4:closing] if closing >= 0 else ""
        if not re.search(r"^name:\s*\S+", front, re.MULTILINE):
            errors.append(f"{rel}: missing name")
        if not re.search(r"^description:\s*.+", front, re.MULTILINE):
            errors.append(f"{rel}: missing description")
        lowered = text.lower()
        for marker, candidates in aliases.items():
            if not any(candidate.lower() in lowered for candidate in candidates):
                warnings.append(f"{rel}: no explicit {marker}/English equivalent marker")
    if errors:
        print("INVALID")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"OK: {len(skills)} active Skill files")
    if warnings:
        print(f"WARNINGS: {len(warnings)}")
        print("\n".join(f"- {warning}" for warning in warnings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
