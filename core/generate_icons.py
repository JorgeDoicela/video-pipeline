#!/usr/bin/env python3
"""
Generador de iconos vectoriales SVG estandarizados para arquitectura de sistemas.
Crea iconos limpios, escalables (viewBox 0 0 24 24) y listos para usar en HyperFrames.
"""

from pathlib import Path

ICONS = {
    "server": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
  <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
  <line x1="6" y1="6" x2="6.01" y2="6"/>
  <line x1="6" y1="18" x2="6.01" y2="18"/>
</svg>""",
    "database": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <ellipse cx="12" cy="5" rx="9" ry="3"/>
  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
</svg>""",
    "cloud": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
</svg>""",
    "docker": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 10h2v2H4zM7 10h2v2H7zM10 10h2v2h-2zM7 7h2v2H7zM10 7h2v2h-2zM13 7h2v2h-2z"/>
  <path d="M22 13c-.5-1-1.5-1.5-2.5-1.5-.5 0-1 .2-1.5.5C17 9 14 8 11 8H2c-.5 0-1 .5-1 1 0 4 3 8 9 8 5.5 0 9.5-3 10.5-6.5.5.3 1 .5 1.5.5z"/>
</svg>""",
    "kubernetes": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polygon points="12 2 21 7 21 17 12 22 3 17 3 7 12 2"/>
  <circle cx="12" cy="12" r="3"/>
  <line x1="12" y1="2" x2="12" y2="9"/>
  <line x1="12" y1="15" x2="12" y2="22"/>
  <line x1="21" y1="7" x2="15" y2="10.5"/>
  <line x1="3" y1="17" x2="9" y2="13.5"/>
  <line x1="21" y1="17" x2="15" y2="13.5"/>
  <line x1="3" y1="7" x2="9" y2="10.5"/>
</svg>""",
    "kafka": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="18" cy="5" r="3"/>
  <circle cx="6" cy="12" r="3"/>
  <circle cx="18" cy="19" r="3"/>
  <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
  <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
</svg>""",
    "redis": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polygon points="12 2 2 7 12 12 22 7 12 2"/>
  <polyline points="2 12 12 17 22 12"/>
  <polyline points="2 17 12 22 22 17"/>
</svg>""",
    "git": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="18" cy="18" r="3"/>
  <circle cx="6" cy="6" r="3"/>
  <path d="M6 9a9 9 0 0 0 9 9"/>
  <line x1="6" y1="9" x2="6" y2="21"/>
</svg>""",
    "cpu": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="4" y="4" width="16" height="16" rx="2"/>
  <rect x="9" y="9" width="6" height="6"/>
  <line x1="9" y1="1" x2="9" y2="4"/>
  <line x1="15" y1="1" x2="15" y2="4"/>
  <line x1="9" y1="20" x2="9" y2="23"/>
  <line x1="15" y1="20" x2="15" y2="23"/>
  <line x1="20" y1="9" x2="23" y2="9"/>
  <line x1="20" y1="15" x2="23" y2="15"/>
  <line x1="1" y1="9" x2="4" y2="9"/>
  <line x1="1" y1="15" x2="4" y2="15"/>
</svg>""",
    "terminal": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="4 17 10 11 4 5"/>
  <line x1="12" y1="19" x2="20" y2="19"/>
</svg>""",
}


def main():
    icons_dir = Path(__file__).resolve().parent.parent / "assets" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    gitkeep = icons_dir / ".gitkeep"
    if gitkeep.exists():
        gitkeep.unlink()

    for name, svg_content in ICONS.items():
        file_path = icons_dir / f"{name}.svg"
        file_path.write_text(svg_content.strip() + "\n", encoding="utf-8")
        print(f"[Icon] Generado: {file_path.name}")


if __name__ == "__main__":
    main()
