"""Install the bundled plotnine_extensions Agent Skill for Claude Code.

This module backs the ``plotnine-extensions-install-skills`` console script. Claude Code
does not scan ``site-packages`` for skills, so the skill shipped inside the
package is copied to where Claude Code looks: by default the personal skill
root, ``~/.claude/skills/plotnine-extensions``, which makes it available in
every project. ``--dest .claude/skills/plotnine-extensions`` installs it into a
single project. Copying is opt-in and never happens on import or
``pip install``.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Optional

SKILL_NAME = "plotnine-extensions"


def bundled_skill_dir() -> Path:
    """Directory of the skill shipped with this package (contains ``SKILL.md``)."""
    return Path(__file__).resolve().parent / "data"


def default_dest() -> Path:
    """``~/.claude/skills/plotnine-extensions``."""
    return Path.home() / ".claude" / "skills" / SKILL_NAME


def install_skill(dest: Optional[Path] = None, force: bool = False) -> Path:
    """Copy the bundled skill to ``dest`` (default :func:`default_dest`).

    An existing ``dest`` is replaced only with ``force``, so that after an
    upgrade the skill matches the installed version exactly.
    """
    src = bundled_skill_dir()
    if not (src / "SKILL.md").is_file():
        raise FileNotFoundError(f"bundled skill not found at {src}; the package may be installed without its data")
    dest = default_dest() if dest is None else Path(dest).expanduser()
    if dest.exists():
        if not force:
            raise FileExistsError(f"{dest} already exists; re-run with --force to overwrite")
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", ".ipynb_checkpoints", ".DS_Store"))
    return dest


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="plotnine-extensions-install-skills",
        description="Install the plotnine_extensions Agent Skill for Claude Code.",
    )
    parser.add_argument("--dest", type=Path, default=None,
                        help=f"destination directory (default: ~/.claude/skills/{SKILL_NAME})")
    parser.add_argument("--force", action="store_true", help="overwrite an existing installation")
    parser.add_argument("--print-path", action="store_true",
                        help="print the bundled skill directory and exit without installing")
    args = parser.parse_args(argv)

    if args.print_path:
        print(bundled_skill_dir())
        return 0
    try:
        dest = install_skill(args.dest, args.force)
    except (FileExistsError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"Installed plotnine_extensions skill to {dest}")
    print("It will be available to Claude Code in your next session.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
