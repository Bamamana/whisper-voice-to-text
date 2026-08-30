#!/usr/bin/env python3
"""Build a single double-clickable Whisper-V1.html from the modular webapp.

Inlines all JS modules (stripping import/export statements) into one HTML
file so it works from file:// with no server.
"""

from pathlib import Path

WEBAPP_DIR = Path(__file__).resolve().parent
OUTPUT = WEBAPP_DIR.parent / "Whisper-V1.html"

# Concatenation order matters (dependencies first).
MODULE_ORDER = [
    "js/providers.js",
    "js/settings.js",
    "js/audio.js",
    "js/transcription.js",
    "js/model-picker.js",
    "js/app.js",
]


def strip_module_syntax(source: str) -> str:
    lines = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") and " from " in stripped:
            continue
        if stripped.startswith("export "):
            line = line.replace("export ", "", 1)
        lines.append(line)
    return "\n".join(lines)


def main() -> None:
    html = (WEBAPP_DIR / "index.html").read_text(encoding="utf-8")

    modules = "\n\n".join(
        strip_module_syntax((WEBAPP_DIR / relative).read_text(encoding="utf-8"))
        for relative in MODULE_ORDER
    )

    script_tag = '<script type="module" src="./js/app.js"></script>'
    if script_tag not in html:
        raise SystemExit("Expected module script tag not found in index.html")

    inlined = html.replace(
        script_tag,
        "<script>\n" + modules + "\n</script>",
    )

    OUTPUT.write_text(inlined, encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(inlined.splitlines())} lines)")


if __name__ == "__main__":
    main()
