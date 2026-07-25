"""
CloudOptima Master Guide — PDF Export
Generates PDF without Chrome headless dependency.
Converts to HTML then attempts multiple PDF backends.
"""

from __future__ import annotations
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = PROJECT_ROOT / "docs" / "CLOUDOPTIMA_MASTER_GUIDE.html"
PDF_PATH = PROJECT_ROOT / "docs" / "CLOUDOPTIMA_MASTER_GUIDE.pdf"

print("=" * 60)
print("  CloudOptima -- Master Guide PDF Export")
print("=" * 60)

if not HTML_PATH.exists():
    print(f"[FAIL] HTML file not found: {HTML_PATH}")
    print("Run 'scripts/export_master_guide.py' first to generate HTML.")
    sys.exit(1)

print(f"[OK] HTML file: {HTML_PATH} ({HTML_PATH.stat().st_size:,} bytes)")

# Try multiple PDF backends
backends = []

# Check for wkhtmltopdf
try:
    r = subprocess.run(["wkhtmltopdf", "--version"], capture_output=True, text=True, timeout=5)
    if r.returncode == 0:
        backends.append(("wkhtmltopdf", r"wkhtmltopdf"))
except (FileNotFoundError, subprocess.TimeoutExpired):
    pass

# Check for weasyprint
try:
    import weasyprint
    backends.append(("weasyprint", "weasyprint"))
except ImportError:
    pass

# Check for Chrome at common paths
chrome_paths = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
]
for cp in chrome_paths:
    p = Path(cp)
    if p.exists():
        backends.append(("chrome", str(p)))
        break

if not backends:
    print("[WARN] No PDF generation backend found.")
    print()
    print("  Options:")
    print("  1. Install wkhtmltopdf: https://wkhtmltopdf.org/downloads.html")
    print("  2. Install weasyprint: pip install weasyprint")
    print("  3. Open HTML in Chrome -> Ctrl+P -> Save as PDF")
    print(f"\n  HTML file: {HTML_PATH}")
    sys.exit(1)

print(f"[OK] Found backends: {', '.join(b[0] for b in backends)}")
backend_name, backend_path = backends[0]
print(f"[..] Using: {backend_name} ({backend_path})")

if backend_name == "wkhtmltopdf":
    result = subprocess.run(
        [backend_path, str(HTML_PATH), str(PDF_PATH)],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        print(f"[OK] PDF generated: {PDF_PATH} ({PDF_PATH.stat().st_size / 1024:.0f} KB)")
    else:
        print(f"[FAIL] wkhtmltopdf failed: {result.stderr[:500]}")

elif backend_name == "weasyprint":
    try:
        weasyprint.HTML(filename=str(HTML_PATH)).write_pdf(str(PDF_PATH))
        print(f"[OK] PDF generated: {PDF_PATH} ({PDF_PATH.stat().st_size / 1024:.0f} KB)")
    except Exception as e:
        print(f"[FAIL] weasyprint failed: {e}")

elif backend_name == "chrome":
    file_url = HTML_PATH.resolve().as_uri()
    result = subprocess.run(
        [backend_path,
         "--headless=new", "--disable-gpu",
         f"--print-to-pdf={PDF_PATH}",
         "--no-margins", "--print-to-pdf-no-header",
         "--no-first-run", "--no-default-browser-check",
         file_url],
        capture_output=True, text=True, timeout=30,
    )
    if PDF_PATH.exists():
        print(f"[OK] PDF generated: {PDF_PATH} ({PDF_PATH.stat().st_size / 1024:.0f} KB)")
    else:
        print(f"[FAIL] Chrome PDF generation failed")
        if result.stderr:
            print(f"  stderr: {result.stderr[:500]}")

print()
if PDF_PATH.exists():
    print(f"  ✅ PDF:  {PDF_PATH}")
    print(f"  ✅ HTML: {HTML_PATH}")
else:
    print(f"  ✅ HTML: {HTML_PATH}")
    print()
    print("  To convert to PDF:")
    print("  1. Open the HTML file in a browser")
    print("  2. Ctrl+P -> Save as PDF")
    print("  3. Check 'Background graphics'")
