#!/usr/bin/env python3
"""Sync the Claude Engineering Skills library into this repository.

Upstream: https://github.com/Soljourner/claude-engineering-skills (MIT)

Upstream nests skills by category (``skills/<category>/<skill>/SKILL.md``, and
``skills/thinking/pump-design/<skill>/SKILL.md``). Claude Code only discovers
project skills at ``.claude/skills/<skill-name>/SKILL.md``, so this script
flattens every skill directory into ``.claude/skills/`` using the ``name`` from
its SKILL.md frontmatter. Upstream docs, inventory and license are copied to
``docs/engineering-skills/``.

Only skills recorded in the manifest from a previous sync are removed or
replaced, so hand-written skills living next to them are left alone.

Usage:
    python scripts/sync_engineering_skills.py            # clone upstream main
    python scripts/sync_engineering_skills.py --ref v1.0 # specific branch/tag
    python scripts/sync_engineering_skills.py --source /path/to/checkout
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM_URL = "https://github.com/Soljourner/claude-engineering-skills.git"
REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DEST = REPO_ROOT / ".claude" / "skills"
DOCS_DEST = REPO_ROOT / "docs" / "engineering-skills"
MANIFEST = DOCS_DEST / "manifest.json"

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
NAME_RE = re.compile(r"^name:\s*['\"]?([A-Za-z0-9_-]+)['\"]?\s*$", re.MULTILINE)


def skill_name(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{skill_md}: missing YAML frontmatter")
    frontmatter = text.split("---", 2)[1]
    match = NAME_RE.search(frontmatter)
    if not match:
        raise ValueError(f"{skill_md}: frontmatter has no 'name'")
    return match.group(1)


def git_head(source: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def sync(source: Path, ref: str | None) -> None:
    skills_root = source / "skills"
    if not skills_root.is_dir():
        sys.exit(f"error: {skills_root} not found")

    skill_dirs = sorted(p.parent for p in skills_root.rglob("SKILL.md"))
    mapping: dict[str, str] = {}
    for skill_dir in skill_dirs:
        name = skill_name(skill_dir / "SKILL.md")
        rel = skill_dir.relative_to(source).as_posix()
        if name in mapping:
            sys.exit(f"error: duplicate skill name {name!r} ({mapping[name]} and {rel})")
        mapping[name] = rel

    previous: set[str] = set()
    if MANIFEST.exists():
        previous = set(json.loads(MANIFEST.read_text())["skills"])

    SKILLS_DEST.mkdir(parents=True, exist_ok=True)
    for name in sorted(previous - mapping.keys()):
        shutil.rmtree(SKILLS_DEST / name, ignore_errors=True)
        print(f"removed  {name}")

    for name, rel in mapping.items():
        dest = SKILLS_DEST / name
        if dest.exists() and name not in previous:
            sys.exit(f"error: {dest} exists and was not created by this script")
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(source / rel, dest, ignore=IGNORE)
        print(f"synced   {name:<32} <- {rel}")

    DOCS_DEST.mkdir(parents=True, exist_ok=True)
    for doc in sorted((source / "docs").glob("*.md")):
        shutil.copy2(doc, DOCS_DEST / doc.name)
    for extra in ("README.md", "SKILLS_INVENTORY.md", "CONTRIBUTING.md", "LICENSE"):
        if (source / extra).exists():
            target = "UPSTREAM_README.md" if extra == "README.md" else extra
            shutil.copy2(source / extra, DOCS_DEST / target)

    MANIFEST.write_text(json.dumps({
        "upstream": UPSTREAM_URL.removesuffix(".git"),
        "ref": ref or "default branch",
        "commit": git_head(source),
        "skills": mapping,
    }, indent=2) + "\n")
    print(f"\n{len(mapping)} skills synced into {SKILLS_DEST.relative_to(REPO_ROOT)}/")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, help="existing local checkout of upstream")
    parser.add_argument("--ref", help="upstream branch or tag to clone")
    args = parser.parse_args()

    if args.source:
        sync(args.source.resolve(), args.ref)
        return

    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "upstream"
        cmd = ["git", "clone", "--depth", "1"]
        if args.ref:
            cmd += ["--branch", args.ref]
        subprocess.run(cmd + [UPSTREAM_URL, str(clone)], check=True)
        sync(clone, args.ref)


if __name__ == "__main__":
    main()
