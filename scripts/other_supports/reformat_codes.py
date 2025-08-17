#!/usr/bin/env python3
"""
Reformat Python files in ui/ to follow the user's preferred style:
- 3 blank lines between top-level classes
- 2 blank lines between top-level functions
- No blank lines inside indented blocks (functions/methods/classes bodies)

Usage:
  python scripts/reformat_ui_style.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def remove_inner_blank_lines(lines: List[str]) -> List[str]:
    """
    Remove blank lines that are INSIDE indented blocks.
    Keep blank lines that separate a block from the next top-level statement.
    Rule: a blank line is removed only if BOTH the previous and next non-empty
    lines are indented (> 0).
    """
    result: List[str] = []
    n = len(lines)


    def indent_of(idx: int) -> int:
        raw = lines[idx]
        return len(raw) - len(raw.lstrip(" \t"))
    # Precompute next non-empty line index for each position
    next_non_empty: List[int] = [-1] * n
    j = n - 1
    last_seen = -1
    while j >= 0:
        if lines[j].strip() != "":
            last_seen = j
        next_non_empty[j] = last_seen
        j -= 1
    prev_non_empty_indent = 0
    for i, line in enumerate(lines):
        if line.strip() == "":
            nxt = next_non_empty[i]
            if nxt == -1:
                # trailing blanks – keep for now; will trim later
                result.append(line)
                continue
            next_indent = indent_of(nxt)
            if prev_non_empty_indent > 0 and next_indent > 0:
                # Inside a block → drop
                continue
            # Otherwise, keep this top-level or boundary blank line
            result.append(line)
            continue
        # non-empty
        prev_non_empty_indent = indent_of(i)
        result.append(line)
    return result


def find_block_starts(lines: List[str]) -> Dict[int, str]:
    """
    Find indices of ANY block starts (at any indentation) and classify as 'class' or 'def'.
    Handles decorators at the same indentation: the first decorator line is treated
    as the block start for the subsequent def/class.
    """
    idx_to_type: Dict[int, str] = {}
    n = len(lines)
    i = 0
    while i < n:
        raw = lines[i]
        stripped = raw.lstrip()
        if stripped.startswith("class "):
            idx_to_type[i] = "class"
        elif stripped.startswith("def "):
            idx_to_type[i] = "def"
        elif stripped.startswith("@"):
            # Decorator: ensure the following def/class has the SAME indentation
            curr_indent = len(raw) - len(stripped)
            j = i + 1
            block_type = None
            while j < n:
                nxt_raw = lines[j]
                nxt_stripped = nxt_raw.lstrip()
                if nxt_stripped == "":
                    j += 1
                    continue
                next_indent = len(nxt_raw) - len(nxt_stripped)
                if next_indent != curr_indent:
                    break
                if nxt_stripped.startswith("class "):
                    block_type = "class"
                    break
                if nxt_stripped.startswith("def "):
                    block_type = "def"
                    break
                if nxt_stripped.startswith("@"):
                    j += 1
                    continue
                break
            if block_type:
                idx_to_type[i] = block_type
        i += 1
    return idx_to_type


def enforce_block_spacing(lines: List[str]) -> List[str]:
    """
    Ensure there are exactly 3 blank lines before classes and 2 before functions,
    for blocks at ANY indentation level. If the block is the very first content
    in the file, do not insert leading blanks.
    """
    idx_to_type = find_block_starts(lines)
    result: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if i in idx_to_type:
            need = 3 if idx_to_type[i] == "class" else 2
            # Strip existing trailing blank lines
            while result and result[-1].strip() == "":
                result.pop()
            # Insert the required number of blank lines if not at file start
            if result:
                for _ in range(need):
                    result.append("\n")
            result.append(lines[i])
            i += 1
            continue
        result.append(lines[i])
        i += 1
    return result


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def reformat_content(text: str) -> str:
    text = normalize_newlines(text)
    lines = [ln if ln.endswith("\n") else ln + "\n" for ln in text.split("\n")]
    # Step 1: Remove inner blank lines in indented blocks
    lines = remove_inner_blank_lines(lines)
    # Step 2: Enforce spacing between blocks (any indentation)
    lines = enforce_block_spacing(lines)
    # Collapse excessive consecutive blank lines at top-level to a single where not controlled
    # (def/class spacing already enforced). Keep at most 2 elsewhere at top-level.
    collapsed: List[str] = []
    blank_run = 0
    for ln in lines:
        if ln.strip() == "":
            blank_run += 1
            # Allow up to 2 in general places (top-level), specific def/class handled already
            if blank_run <= 2:
                collapsed.append(ln)
        else:
            blank_run = 0
            collapsed.append(ln)
    # Remove trailing blank lines at EOF
    while collapsed and collapsed[-1].strip() == "":
        collapsed.pop()
    collapsed.append("\n")
    return "".join(collapsed)


def collect_python_files(paths: List[Path]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        if p.is_file() and p.suffix == ".py":
            files.append(p)
        elif p.is_dir():
            files.extend(list(p.rglob("*.py")))
    return files


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    # If args are provided, treat them as target directories/files; otherwise default to ui/
    args = sys.argv[1:]
    target_paths: List[Path] = []
    if args:
        for a in args:
            p = (repo_root / a).resolve()
            target_paths.append(p)
    else:
        target_paths = [repo_root / "ui"]
    targets = collect_python_files(target_paths)
    changed: List[Tuple[Path, int]] = []
    for path in targets:
        original = read_text(path)
        reformatted = reformat_content(original)
        if reformatted != original:
            write_text(path, reformatted)
            changed.append((path, len(reformatted)))
    if args:
        scope = ", ".join(args)
    else:
        scope = "ui/"
    print(f"Reformatted {len(changed)} files in {scope}.")
    for p, _ in changed:
        print(f" - {p.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

