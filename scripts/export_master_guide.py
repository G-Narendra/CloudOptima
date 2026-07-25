"""
Export CloudOptima Master Guide to PDF.

Usage:
    python scripts/export_master_guide.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MD_PATH = PROJECT_ROOT / "docs" / "CLOUDOPTIMA_MASTER_GUIDE.md"
HTML_PATH = PROJECT_ROOT / "docs" / "CLOUDOPTIMA_MASTER_GUIDE.html"
PDF_PATH = PROJECT_ROOT / "docs" / "CLOUDOPTIMA_MASTER_GUIDE.pdf"

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def process_inline(text: str) -> str:
    """Process inline markdown formatting (bold, italic, code, links)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code class='inline-code'>\1</code>", text)
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"[\1]", text)
    text = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def convert_md_to_html(md_text: str) -> str:
    """Convert markdown text to styled HTML."""
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
                html_parts.append(f'<pre class="code-block"><code class="language-{code_lang}">{escaped}</code></pre>')
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

        if not line.strip():
            flush_table()
            flush_list()
            html_parts.append("")
            continue

        if line.strip() == "---":
            flush_table()
            flush_list()
            html_parts.append('<hr class="section-divider">')
            continue

        h_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if h_match:
            flush_table()
            flush_list()
            level = len(h_match.group(1))
            text = h_match.group(2).strip()
            text = process_inline(text)
            anchor = re.sub(r"[^\w\-]+", "-", text.lower()).strip("-")
            html_parts.append(f"<h{level} id='{anchor}'>{text}</h{level}>")
            continue

        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            is_separator = all(re.match(r"^:?-+:?$", c) for c in cells if c)

            if not in_table:
                if is_separator:
                    html_parts.append("<table><tbody>")
                    in_table = True
                else:
                    header_cells = "</th><th>".join(cells)
                    html_parts.append(f"<table><thead><tr><th>{header_cells}</th></tr></thead><tbody>")
                    in_table = True
            elif is_separator:
                pass
            else:
                data_cells = "</td><td>".join(process_inline(c) for c in cells)
                html_parts.append(f"<tr><td>{data_cells}</td></tr>")
            continue

        if in_table:
            flush_table()

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
            html_parts.append(f"<li class=\"{'checked' if checked else 'unchecked'}\">{icon} {content}</li>")
            continue

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

        if line.startswith(">"):
            content = line.lstrip("> ").strip()
            html_parts.append(f"<blockquote>{content}</blockquote>")
            continue

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
<title>CloudOptima — Master Technical Guide</title>
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
        margin: 1.5rem 0 0.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid rgba(108, 92, 231, 0.3);
    }}

    h2 {{
        font-size: 1.6rem;
        font-weight: 700;
        color: #a29bfe;
        margin: 2rem 0 0.8rem;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid rgba(162, 155, 254, 0.2);
    }}

    h3 {{
        font-size: 1.2rem;
        font-weight: 600;
        color: #c0b8ff;
        margin: 1.5rem 0 0.5rem;
    }}

    h4 {{
        font-size: 1.05rem;
        font-weight: 600;
        color: #ddd;
        margin: 1rem 0 0.3rem;
    }}

    h5, h6 {{
        font-size: 0.95rem;
        font-weight: 500;
        color: #bbb;
        margin: 0.8rem 0 0.3rem;
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

    @media print {{
        body {{ background: white; color: #333; padding: 0.5in; font-size: 10pt; }}
        h1, h2, h3 {{ -webkit-text-fill-color: initial; background: none; color: #6C5CE7; }}
        p, li, td {{ color: #444; }}
        .code-block {{ background: #f5f5ff; border-color: #ddd; color: #333; }}
        table th {{ background: #eee; color: #333; }}
        table td, table th {{ border-color: #ddd; }}
        blockquote {{ background: #f8f6ff; border-left-color: #6C5CE7; color: #555; }}
        a {{ color: #6C5CE7; text-decoration: none; }}
    }}
</style>
</head>
<body>
{markdown_html}
</body>
</html>"""


def main():
    print("=" * 60)
    print("  CloudOptima -- Master Guide PDF Export")
    print("=" * 60)

    if not MD_PATH.exists():
        print(f"[FAIL] Markdown file not found: {MD_PATH}")
        sys.exit(1)
    print(f"[OK] Found markdown: {MD_PATH}")

    md_text = MD_PATH.read_text(encoding="utf-8")
    print(f"[OK] Read {len(md_text)} characters ({len(md_text.splitlines())} lines)")

    print("[..] Converting markdown to HTML...")
    content_html = convert_md_to_html(md_text)
    full_html = build_html(content_html)
    HTML_PATH.write_text(full_html, encoding="utf-8")
    print(f"[OK] HTML written: {HTML_PATH} ({len(full_html):,} bytes)")

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
            result = subprocess.run([cp, "--version"], capture_output=True, timeout=5, text=True)
            if result.returncode == 0:
                chrome_exe = cp
                break
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError, OSError):
            continue

    if chrome_exe:
        print(f"[OK] Found Chrome at: {chrome_exe}")
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
                timeout=60,
                text=True,
            )
            if PDF_PATH.exists():
                size_kb = PDF_PATH.stat().st_size / 1024
                print(f"[OK] PDF generated: {PDF_PATH} ({int(size_kb)} KB)")
            else:
                print("[WARN] Chrome ran but PDF was not created")
                if result.stderr:
                    print(f"  stderr: {result.stderr[:500]}")
        except Exception as e:
            print(f"[WARN] Chrome PDF generation failed: {e}")
    else:
        print("[WARN] Chrome not found. Generating HTML only.")

    print()
    print("=" * 60)
    print("  Done!")
    print()
    print(f"  HTML: {HTML_PATH}")
    if PDF_PATH.exists():
        print(f"  PDF:  {PDF_PATH}")
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
