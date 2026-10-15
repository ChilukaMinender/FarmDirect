from pathlib import Path

replacements = {
    "ðŸ‘¨": "👨",
    "ðŸ“": "📍",
    "ðŸŒ¿": "🌿",
    "ðŸŒ±": "🌱",
    "ðŸ”Ž": "🔎",
    "ðŸ›’": "🛒",
    "ðŸŒ¾": "🌾",
    "â†": "←",
    "â†’": "→",
    "âœ“": "✓",
    "â‚¹": "₹",
}

updated = 0

for folder in ("templates", "static"):
    root = Path(folder)

    if not root.exists():
        continue

    for file in root.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in (
            ".html", ".css", ".js"
        ):
            continue

        try:
            original = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        fixed = original

        for wrong, correct in replacements.items():
            fixed = fixed.replace(wrong, correct)

        if fixed != original:
            file.write_text(fixed, encoding="utf-8")
            print("Fixed:", file)
            updated += 1

print(f"\nCompleted. Updated {updated} file(s).")