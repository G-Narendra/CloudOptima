"""
Export CloudOptima Technical Deep Dive to PDF.

Reads the markdown document, wraps it in a clean HTML template
with Mermaid.js CDN for diagram rendering, and uses Chrome
headless mode to produce a presentation-quality PDF.

Usage:
    python scripts/export_pdf.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MD_PATH = PROJECT_ROOT / "docs" / "CLOUDOPTIMA_TECHNICAL_DEEP_DIVE.md"
HTML_PATH = PROJECT_ROOT / "docs" / "CLOUDOPTIMA_TECHNICAL_DEEP_DIVE.html"
PDF_PATH = PROJECT_ROOT / "docs" / "CLOUDOPTIMA_TECHNICAL_DEEP_DIVE.pdf"

# Use UTF-8 for stdout to support emoji and special chars
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore


def process_inline(text: str) -> str:
    """Process inline markdown formatting (bold, italic, code, links)."""
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code class='inline-code'>\1</code>", text)
    # Image (ignore, use alt text)
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"[\1]", text)
    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def convert_md_to_html(md_text: str) -> str:
    """Convert markdown text to styled HTML with Mermaid support."""
    lines = md_text.split("\n")
    html_parts: list[str] = []
    in_code_block = False
    code_lang = ""
    code_content: list[str] = []
    in_table = False
    in_list = False
    list_type: str = "ul"

    def flush_code():
        nonlocal in_code_block, code_lang, code_content
        if in_code_block:
            raw = "\n".join(code_content)
            if code_lang == "mermaid":
                html_parts.append('<div class="mermaid">\n' + raw + '\n</div>')
            else:
                escaped = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_parts.append(
                    f'<pre class="code-block"><code class="language-{code_lang}">{escaped}</code></pre>'
                )
            code_content = []
            in_code_block = False
            code_lang = ""

    def flush_table():
        nonlocal in_table
        if in_table:
            html_parts.append("</tbody></table>\n")
            in_table = False

    def flush_list():
        nonlocal in_list
        if in_list:
            html_parts.append(f"</{list_type}>\n")
            in_list = False

    for line in lines:
        # ── Code fences ──────────────────────────────────────────────
        if line.startswith("```"):
            if in_code_block:
                flush_code()
            else:
                flush_table()
                flush_list()
                in_code_block = True
                code_lang = line[3:].strip()
            continue

        if in_code_block:
            code_content.append(line)
            continue

        # ── Empty lines ──────────────────────────────────────────────
        if not line.strip():
            flush_table()
            flush_list()
            html_parts.append("")
            continue

        # ── Horizontal rule ──────────────────────────────────────────
        if line.strip() == "---":
            flush_table()
            flush_list()
            html_parts.append('<hr class="section-divider">')
            continue

        # ── Headers (h1 - h6) ────────────────────────────────────────
        h_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if h_match:
            flush_table()
            flush_list()
            level = len(h_match.group(1))
            text = h_match.group(2).strip()
            # Process inline formatting
            text = process_inline(text)
            anchor = re.sub(r"[^\w\-]+", "-", text.lower()).strip("-")
            html_parts.append(f"<h{level} id='{anchor}'>{text}</h{level}>")
            continue

        # ── Tables ───────────────────────────────────────────────────
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            is_separator = all(re.match(r"^:?-+:?$", c) for c in cells if c)

            if not in_table:
                if is_separator:
                    # Header-less table: open table + tbody
                    html_parts.append("<table><tbody>")
                    in_table = True
                else:
                    # Header row: open table + thead
                    header_cells = "</th><th>".join(cells)
                    html_parts.append(f"<table><thead><tr><th>{header_cells}</th></tr></thead><tbody>")
                    in_table = True
            elif is_separator:
                # Separator in middle of table — ignore
                pass
            else:
                # Data row
                data_cells = "</td><td>".join(process_inline(c) for c in cells)
                html_parts.append(f"<tr><td>{data_cells}</td></tr>")
            continue

        if in_table:
            flush_table()

        # ── Checkbox list ────────────────────────────────────────────
        cb_match = re.match(r"^(\s*)- \[([ x])\]\s+(.*)", line)
        if cb_match:
            if not in_list or list_type != "ul":
                flush_list()
                html_parts.append("<ul class='checklist'>")
                in_list = True
                list_type = "ul"
            checked = cb_match.group(2) == "x"
            content = process_inline(cb_match.group(3).strip())
            icon = "&#9989;" if checked else "&#9632;"
            html_parts.append(f"<li class='{'checked' if checked else 'unchecked'}'>{icon} {content}</li>")
            continue

        # ── Unordered list ───────────────────────────────────────────
        ul_match = re.match(r"^(\s*)[-*+]\s+(.*)", line)
        if ul_match:
            if not in_list or list_type != "ul":
                flush_list()
                html_parts.append("<ul>")
                in_list = True
                list_type = "ul"
            content = process_inline(ul_match.group(2).strip())
            html_parts.append(f"<li>{content}</li>")
            continue

        # ── Ordered list ─────────────────────────────────────────────
        ol_match = re.match(r"^(\s*)\d+\.\s+(.*)", line)
        if ol_match:
            if not in_list or list_type != "ol":
                flush_list()
                html_parts.append("<ol>")
                in_list = True
                list_type = "ol"
            content = process_inline(ol_match.group(2).strip())
            html_parts.append(f"<li>{content}</li>")
            continue

        flush_list()

        # ── Blockquote ───────────────────────────────────────────────
        if line.startswith(">"):
            content = line.lstrip("> ").strip()
            html_parts.append(f"<blockquote>{content}</blockquote>")
            continue

        # ── Regular paragraph ────────────────────────────────────────
        processed = process_inline(line.strip())
        if processed:
            html_parts.append(f"<p>{processed}</p>")

    flush_code()
    flush_table()
    flush_list()

    return "\n".join(html_parts)


def build_html(markdown_html: str) -> str:
    """Wrap markdown HTML in a complete, styled HTML document."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CloudOptima — Technical Deep Dive</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {{
    mermaid.initialize({{
        startOnLoad: true,
        theme: 'dark',
        themeVariables: {{
            primaryColor: '#6C5CE7',
            primaryTextColor: '#fff',
            primaryBorderColor: '#6C5CE7',
            lineColor: '#a29bfe',
            secondaryColor: '#2d2d5e',
            tertiaryColor: '#1a1a2e',
            background: '#0d0d1a',
            mainBkg: '#1a1a2e',
            nodeBorder: '#6C5CE7',
            clusterBkg: '#111122',
            clusterBorder: '#2d2d5e',
            titleColor: '#e0e0f0',
            edgeLabelBackground: '#1a1a2e',
            nodeTextColor: '#e0e0f0'
        }}
    }});
}});
</script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: #0d0d1a;
        color: #e0e0f0;
        line-height: 1.7;
        max-width: 1100px;
        margin: 0 auto;
        padding: 40px 60px;
    }}

    h1 {{
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6C5CE7, #a29bfe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 1.5rem 0 0.5rem 0;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid rgba(108, 92, 231, 0.3);
    }}

    h2 {{
        font-size: 1.6rem;
        font-weight: 700;
        color: #a29bfe;
        margin: 2rem 0 0.8rem 0;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid rgba(162, 155, 254, 0.2);
    }}

    h3 {{
        font-size: 1.2rem;
        font-weight: 600;
        color: #c0b8ff;
        margin: 1.5rem 0 0.5rem 0;
    }}

    h4 {{
        font-size: 1.05rem;
        font-weight: 600;
        color: #ddd;
        margin: 1rem 0 0.3rem 0;
    }}

    p {{ margin: 0.6rem 0; color: #ccc; }}

    blockquote {{
        background: rgba(108, 92, 231, 0.1);
        border-left: 4px solid #6C5CE7;
        padding: 0.8rem 1.2rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
        font-style: italic;
        color: #bbb;
    }}

    blockquote strong {{ color: #a29bfe; }}

    .code-block {{
        background: #111122;
        border: 1px solid #2d2d5e;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.8rem 0;
        overflow-x: auto;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        line-height: 1.5;
        color: #a0d0ff;
    }}

    code.inline-code {{
        background: rgba(108, 92, 231, 0.15);
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85em;
        color: #a29bfe;
    }}

    .section-divider {{
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(108, 92, 231, 0.3), transparent);
        margin: 2rem 0;
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
        font-size: 0.85rem;
    }}

    th {{
        background: rgba(108, 92, 231, 0.15);
        color: #a29bfe;
        font-weight: 600;
        padding: 0.5rem 0.8rem;
        text-align: left;
        border: 1px solid #2d2d5e;
    }}

    td {{
        padding: 0.4rem 0.8rem;
        border: 1px solid #2d2d5e;
        color: #ccc;
    }}

    tr:nth-child(even) td {{
        background: rgba(255, 255, 255, 0.02);
    }}

    ul, ol {{ margin: 0.5rem 0 0.5rem 1.5rem; }}
    li {{ margin: 0.2rem 0; color: #ccc; }}

    ul.checklist {{ list-style: none; margin-left: 0; }}
    ul.checklist li {{ padding: 0.2rem 0; }}
    ul.checklist li.checked {{ color: #10B981; }}
    ul.checklist li.unchecked {{ color: #888; }}

    .mermaid {{
        background: #111122;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1.2rem 0;
        text-align: center;
        border: 1px solid #2d2d5e;
        overflow-x: auto;
    }}

    @media print {{
        body {{
            background: white;
            color: #333;
            padding: 0.5in;
            font-size: 10pt;
        }}
        h1, h2, h3 {{
            -webkit-text-fill-color: initial;
            background: none;
            color: #6C5CE7;
        }}
        h2 {{ color: #6C5CE7; }}
        h3 {{ color: #555; }}
        p, li, td {{ color: #444; }}
        .code-block {{ background: #f5f5ff; border-color: #ddd; color: #333; }}
        table th {{ background: #eee; color: #333; }}
        table td, table th {{ border-color: #ddd; }}
        .mermaid {{ background: white; border: 1px solid #ddd; }}
        blockquote {{ background: #f8f6ff; border-left-color: #6C5CE7; color: #555; }}
        a {{ color: #6C5CE7; text-decoration: none; }}
    }}
</style>
</head>
<body>
{markdown_html}
<script>mermaid.run({{ querySelector: '.mermaid' }});</script>
</body>
</html>"""


def main():
    print("=" * 60)
    print("  CloudOptima -- PDF Export Tool")
    print("=" * 60)

    if not MD_PATH.exists():
        print("[FAIL] Markdown file not found: " + str(MD_PATH))
        sys.exit(1)
    print("[OK] Found markdown: " + str(MD_PATH))

    md_text = MD_PATH.read_text(encoding="utf-8")
    print("[OK] Read " + str(len(md_text)) + " characters")

    print("[..] Converting markdown to HTML with Mermaid CDN...")
    content_html = convert_md_to_html(md_text)
    full_html = build_html(content_html)
    HTML_PATH.write_text(full_html, encoding="utf-8")
    print("[OK] HTML written to: " + str(HTML_PATH))
    print("     (" + str(len(full_html)) + " bytes)")

    # Try Chrome headless PDF generation
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
        "chrome",
        "google-chrome",
        "google-chrome-stable",
    ]

    chrome_exe = None
    for cp in chrome_paths:
        try:
            result = subprocess.run(
                [cp, "--version"],
                capture_output=True,
                timeout=5,
                text=True,
            )
            if result.returncode == 0:
                chrome_exe = cp
                break
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError, OSError):
            continue

    if chrome_exe:
        print("[OK] Found Chrome at: " + chrome_exe)
        print("[..] Generating PDF via Chrome headless...")

        file_url = HTML_PATH.resolve().as_uri()

        try:
            result = subprocess.run(
                [
                    chrome_exe,
                    "--headless=new",
                    "--disable-gpu",
                    f"--print-to-pdf={PDF_PATH}",
                    "--no-margins",
                    "--print-to-pdf-no-header",
                    file_url,
                ],
                capture_output=True,
                timeout=30,
                text=True,
            )
            if PDF_PATH.exists():
                size_kb = PDF_PATH.stat().st_size / 1024
                print("[OK] PDF generated: " + str(PDF_PATH) + " (" + str(int(size_kb)) + " KB)")
            else:
                print("[WARN] Chrome ran but PDF was not created")
                if result.stderr:
                    print("  stderr:", result.stderr[:500])
        except Exception as e:
            print("[WARN] Chrome PDF generation failed: " + str(e))
    else:
        print("[WARN] Chrome not found for headless PDF generation.")

    print()
    print("=" * 60)
    print("  Done!")
    print()
    print("  HTML: " + str(HTML_PATH))
    if PDF_PATH.exists():
        print("  PDF:  " + str(PDF_PATH))
    else:
        print()
        print("  To print as PDF from Chrome manually:")
        print("  1. Open the HTML file in Chrome")
        print("  2. Press Ctrl+P")
        print("  3. Select 'Save as PDF'")
        print("  4. Check 'Background graphics' in More settings")
        print("  5. Save")
    print("=" * 60)


if __name__ == "__main__":
    main()
