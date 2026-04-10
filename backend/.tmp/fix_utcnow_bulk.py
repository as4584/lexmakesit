from __future__ import annotations

import pathlib
import re
import sys


def ensure_timezone_import(content: str) -> str:
    lines = content.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        if line.startswith("from datetime import"):
            if "timezone" not in line:
                if line.rstrip().endswith("\\"):
                    continue
                if "#" in line:
                    head, comment = line.split("#", 1)
                    head = head.rstrip() + ", timezone"
                    if line.endswith("\n"):
                        head += "\n"
                    lines[idx] = head + "#" + comment
                else:
                    newline = "\n" if line.endswith("\n") else ""
                    lines[idx] = line.rstrip("\n").rstrip() + ", timezone" + newline
            return "".join(lines)
    return content


def patch_file(path: pathlib.Path) -> bool:
    original = path.read_text(encoding="utf-8")
    if "datetime.utcnow" not in original:
        return False

    updated = original
    updated = updated.replace("datetime.utcnow()", "datetime.now(timezone.utc)")
    updated = re.sub(
        r"datetime\.utcnow(?!\s*\()",
        "lambda: datetime.now(timezone.utc)",
        updated,
    )
    updated = ensure_timezone_import(updated)

    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python fix_utcnow_bulk.py <root>")
        return 2

    root = pathlib.Path(sys.argv[1])
    changed = 0
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if path.name.endswith(".bak") or ".bak_" in path.name:
            continue
        if patch_file(path):
            changed += 1
            print(path)

    print(f"changed_files={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
