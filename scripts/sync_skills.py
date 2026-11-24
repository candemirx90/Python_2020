#!/usr/bin/env python3
"""Sync third-party Agent Skills libraries into this repository.

Claude Code discovers project skills only at ``.claude/skills/<name>/SKILL.md``.
Upstream libraries keep their skills elsewhere (nested category folders, or
``.agents/skills/``), so this script copies every directory that holds a
SKILL.md into ``.claude/skills/<name>/`` using the ``name`` from its
frontmatter. Each source's docs and license go to ``docs/<source>/``, together
with a ``manifest.json`` recording the upstream commit and which skills it owns.

A skill is only replaced or removed by the source whose manifest lists it, so
skills from other sources or written by hand are never touched.

Usage:
    python scripts/sync_skills.py                         # every source
    python scripts/sync_skills.py engineering-skills      # one source
    python scripts/sync_skills.py mechanical-3dcad-design-agent --ref v0.8.1
    python scripts/sync_skills.py engineering-skills --checkout /path/to/clone
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DEST = REPO_ROOT / ".claude" / "skills"
DOCS_ROOT = REPO_ROOT / "docs"
NAME_RE = re.compile(r"^name:\s*['\"]?([A-Za-z0-9_-]+)['\"]?\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Source:
    url: str
    skills_root: str
    # Files or globs (relative to the upstream root) copied into docs/<source>/.
    docs: tuple[str, ...]
    # Directory/file names left out of each copied skill.
    skill_excludes: tuple[str, ...] = field(default=())
    # Upstream file -> name in docs/<source>/ (to avoid clashing with ours).
    renames: tuple[tuple[str, str], ...] = field(default=())


SOURCES: dict[str, Source] = {
    "engineering-skills": Source(
        url="https://github.com/Soljourner/claude-engineering-skills",
        skills_root="skills",
        docs=("docs/*.md", "README.md", "SKILLS_INVENTORY.md", "CONTRIBUTING.md", "LICENSE"),
        renames=(("README.md", "UPSTREAM_README.md"),),
    ),
    "mechanical-3dcad-design-agent": Source(
        url="https://github.com/Milkdomeda/ai-mechanical-3dcad-design-agent",
        skills_root=".agents/skills",
        docs=("docs/*.md", "README.md", "AGENTS.md", "CHANGELOG.md", "LICENSE",
              "THIRD_PARTY_NOTICES.md", ".env.example"),
        # agents/openai.yaml is Codex-only metadata.
        skill_excludes=("agents",),
        renames=(("README.md", "UPSTREAM_README.md"), ("AGENTS.md", "UPSTREAM_AGENTS.md"),
                 (".env.example", "env.example")),
    ),
    "text-to-cad": Source(
        url="https://github.com/earthtojake/text-to-cad",
        skills_root="skills",
        docs=("README.md", "AGENTS.md", "LICENSE", "SECURITY.md", "VERSION", "docs/install.md",
              "docs/migrations/*.md"),
        skill_excludes=("agents",),
        renames=(("README.md", "UPSTREAM_README.md"), ("AGENTS.md", "UPSTREAM_AGENTS.md")),
    ),
}

BASE_IGNORES = ("__pycache__", "*.pyc", ".DS_Store")


def manifest_path(source_id: str) -> Path:
    return DOCS_ROOT / source_id / "manifest.json"


def owned_skills(source_id: str) -> set[str]:
    path = manifest_path(source_id)
    return set(json.loads(path.read_text())["skills"]) if path.exists() else set()


def skill_name(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise SystemExit(f"error: {skill_md}: missing YAML frontmatter")
    match = NAME_RE.search(text.split("---", 2)[1])
    if not match:
        raise SystemExit(f"error: {skill_md}: frontmatter has no 'name'")
    return match.group(1)


def git_head(checkout: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def sync(source_id: str, checkout: Path, ref: str | None) -> None:
    src = SOURCES[source_id]
    skills_root = checkout / src.skills_root
    if not skills_root.is_dir():
        raise SystemExit(f"error: {skills_root} not found")

    mapping: dict[str, str] = {}
    for skill_md in sorted(skills_root.rglob("SKILL.md")):
        name = skill_name(skill_md)
        rel = skill_md.parent.relative_to(checkout).as_posix()
        if name in mapping:
            raise SystemExit(f"error: duplicate skill {name!r} ({mapping[name]} and {rel})")
        mapping[name] = rel

    mine = owned_skills(source_id)
    others = {n: sid for sid in SOURCES if sid != source_id for n in owned_skills(sid)}
    for name in mapping:
        if name in others:
            raise SystemExit(f"error: skill {name!r} is already provided by {others[name]}")
        if (SKILLS_DEST / name).exists() and name not in mine:
            raise SystemExit(f"error: .claude/skills/{name} exists and is not owned by {source_id}")

    SKILLS_DEST.mkdir(parents=True, exist_ok=True)
    for name in sorted(mine - mapping.keys()):
        shutil.rmtree(SKILLS_DEST / name, ignore_errors=True)
        print(f"removed  {name}")

    ignore = shutil.ignore_patterns(*BASE_IGNORES, *src.skill_excludes)
    for name, rel in mapping.items():
        dest = SKILLS_DEST / name
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(checkout / rel, dest, ignore=ignore)
        print(f"synced   {name:<32} <- {rel}")

    docs_dest = DOCS_ROOT / source_id
    docs_dest.mkdir(parents=True, exist_ok=True)
    renames = dict(src.renames)
    for pattern in src.docs:
        for path in sorted(checkout.glob(pattern)):
            rel = path.relative_to(checkout).as_posix()
            shutil.copy2(path, docs_dest / renames.get(rel, path.name))

    manifest_path(source_id).write_text(json.dumps({
        "upstream": src.url,
        "ref": ref or "default branch",
        "commit": git_head(checkout),
        "skills": mapping,
    }, indent=2) + "\n")
    print(f"{source_id}: {len(mapping)} skills synced\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sources", nargs="*", metavar="source",
                        help=f"source(s) to sync: {', '.join(SOURCES)} (default: all)")
    parser.add_argument("--ref", help="upstream branch or tag (single source only)")
    parser.add_argument("--checkout", type=Path, help="existing local clone (single source only)")
    args = parser.parse_args()

    selected = args.sources or list(SOURCES)
    unknown = [s for s in selected if s not in SOURCES]
    if unknown:
        parser.error(f"unknown source(s): {', '.join(unknown)} (choose from {', '.join(SOURCES)})")
    if (args.ref or args.checkout) and len(selected) != 1:
        parser.error("--ref and --checkout need exactly one source")

    for source_id in selected:
        if args.checkout:
            sync(source_id, args.checkout.resolve(), args.ref)
            continue
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / source_id
            cmd = ["git", "clone", "--depth", "1", *(["--branch", args.ref] if args.ref else [])]
            subprocess.run([*cmd, SOURCES[source_id].url + ".git", str(clone)], check=True)
            sync(source_id, clone, args.ref)


if __name__ == "__main__":
    sys.exit(main())
