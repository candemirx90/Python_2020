#!/usr/bin/env python3
"""Sync third-party Agent Skills libraries into this repository.

Claude Code discovers project skills only at ``.claude/skills/<name>/SKILL.md``.
Upstream libraries keep their skills elsewhere (nested category folders, or
``.agents/skills/``), so this script copies every directory that holds a
SKILL.md into ``.claude/skills/<name>/`` using the ``name`` from its
frontmatter. Upstreams that ship no SKILL.md directory at all (Graphify keeps
its skill body and references in its Python package) list the files that make
up the skill instead. Each source's docs and license go to ``docs/<source>/``, together
with a ``manifest.json`` recording the upstream commit and which skills it owns.

A skill is only replaced or removed by the source whose manifest lists it, so
skills from other sources or written by hand are never touched.

Usage:
    python scripts/sync_skills.py                         # every source
    python scripts/sync_skills.py engineering-skills      # one source
    python scripts/sync_skills.py mechanical-3dcad-design-agent --ref v0.8.1
    python scripts/sync_skills.py engineering-skills --checkout /path/to/clone
    python scripts/sync_skills.py graphify --ref v0.9.122
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
    # Folder scanned for SKILL.md directories ("" when the source only uses `assembled`).
    skills_root: str
    # Files or globs (relative to the upstream root) copied into docs/<source>/.
    docs: tuple[str, ...]
    # Directory/file names left out of each copied skill.
    skill_excludes: tuple[str, ...] = field(default=())
    # Upstream file -> name in docs/<source>/ (to avoid clashing with ours).
    renames: tuple[tuple[str, str], ...] = field(default=())
    # Skills built from explicit upstream paths, for upstreams with no SKILL.md
    # directory: each entry is ((upstream path, path inside the skill), ...) and
    # must map one upstream file to "SKILL.md".
    assembled: tuple[tuple[tuple[str, str], ...], ...] = field(default=())


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
    "last30days": Source(
        url="https://github.com/mvanhorn/last30days-skill",
        skills_root="skills",
        docs=("README.md", "LICENSE", "SECURITY.md", "CONFIGURATION.md", "CONCEPTS.md", "CHANGELOG.md"),
        # Upstream's .skillignore leaves the demo media (assets/, ~14 MB) and Codex metadata out
        # of the runtime skill. Its Stop hook (.claude-plugin/hooks.json) is plugin-only and not
        # installed here.
        skill_excludes=("agents", "assets"),
        renames=(("README.md", "UPSTREAM_README.md"),),
    ),
    "graphify": Source(
        url="https://github.com/safishamsi/graphify",
        skills_root="",
        docs=("README.md", "LICENSE", "LICENSE-MIT", "NOTICE", "SECURITY.md", "ARCHITECTURE.md",
              "docs/how-it-works.md"),
        renames=(("README.md", "UPSTREAM_README.md"),),
        # What `graphify claude install --project` copies. That installer also writes a CLAUDE.md
        # block, PreToolUse/SessionStart hooks in .claude/settings.json and a .graphify_version
        # stamp; none of those are installed here.
        assembled=((("graphify/skill.md", "SKILL.md"),
                    ("graphify/skills/claude/references", "references")),),
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


def discover(src: Source, checkout: Path) -> dict[str, tuple[tuple[str, str], ...]]:
    """Map each skill name to its parts: (upstream path, path inside the skill)."""
    found: dict[str, tuple[tuple[str, str], ...]] = {}

    def add(name: str, parts: tuple[tuple[str, str], ...]) -> None:
        if name in found:
            raise SystemExit(f"error: duplicate skill {name!r} ({found[name][0][0]} and {parts[0][0]})")
        found[name] = parts

    if src.skills_root:
        skills_root = checkout / src.skills_root
        if not skills_root.is_dir():
            raise SystemExit(f"error: {skills_root} not found")
        for skill_md in sorted(skills_root.rglob("SKILL.md")):
            add(skill_name(skill_md), ((skill_md.parent.relative_to(checkout).as_posix(), "."),))

    for parts in src.assembled:
        skill_md = [up for up, inside in parts if inside == "SKILL.md"]
        if len(skill_md) != 1:
            raise SystemExit(f"error: assembled skill {parts!r} needs exactly one SKILL.md")
        for up, _ in parts:
            if not (checkout / up).exists():
                raise SystemExit(f"error: {checkout / up} not found")
        add(skill_name(checkout / skill_md[0]), parts)
    return found


def copy_skill(checkout: Path, parts: tuple[tuple[str, str], ...], dest: Path, ignore) -> None:
    for up, inside in parts:
        source, target = checkout / up, dest / inside
        if source.is_dir():
            shutil.copytree(source, target, ignore=ignore, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def manifest_entry(parts: tuple[tuple[str, str], ...]) -> str | dict[str, str]:
    # A plain upstream folder stays a string, as in existing manifests.
    if len(parts) == 1 and parts[0][1] == ".":
        return parts[0][0]
    return {inside: up for up, inside in parts}


def sync(source_id: str, checkout: Path, ref: str | None) -> None:
    src = SOURCES[source_id]
    mapping = discover(src, checkout)

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
    for name, parts in mapping.items():
        dest = SKILLS_DEST / name
        shutil.rmtree(dest, ignore_errors=True)
        copy_skill(checkout, parts, dest, ignore)
        print(f"synced   {name:<32} <- {', '.join(up for up, _ in parts)}")

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
        "skills": {name: manifest_entry(parts) for name, parts in mapping.items()},
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
