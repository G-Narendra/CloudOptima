"""
Comprehensive audit of CloudOptima Master Guide HTML.
Checks: TOC links vs heading IDs, tag balance, code blocks, stray chars.
Outputs ASCII only (no Unicode) for Windows terminal compatibility.
"""
from pathlib import Path
import re
from collections import Counter

html = Path("docs/CLOUDOPTIMA_MASTER_GUIDE.html").read_text("utf-8", errors="replace")

print("=" * 60)
print("CLOUDOPTIMA MASTER GUIDE - AUDIT REPORT")
print("=" * 60)
print()

# ─── 1. TOC vs HEADING ID CHECK ───────────────────────────
print("--- TOC hrefs vs Heading IDs ---")
toc_hrefs = re.findall(r'href="#([^"]+)"', html)
heading_ids = re.findall(r"id='([^']+)'", html)

broken = 0
for href in toc_hrefs:
    if re.match(r"^\d+-", href):  # Only section links
        if href not in heading_ids:
            print(f"  BROKEN: href=#{href} has NO matching heading id")
            broken += 1
        else:
            count = heading_ids.count(href)
            if count > 1:
                print(f"  DUPLICATE: id '{href}' appears {count} times")

if broken == 0:
    print("  All TOC links match heading IDs. OK")

# ─── 2. TAG BALANCE CHECK ─────────────────────────────────
print()
print("--- HTML Tag Balance ---")
tags_to_check = ["h1","h2","h3","h4","h5","h6","table","thead","tbody","tr","th",
                  "td","ul","ol","li","pre","code","blockquote","p","div","span",
                  "a","strong","em"]

open_counts = {}
close_counts = {}
for tag in tags_to_check:
    open_counts[tag] = len(re.findall(rf"<{tag}(?:\s|>)", html))
    close_counts[tag] = len(re.findall(rf"</{tag}>", html))

imbalance = False
for tag in tags_to_check:
    diff = open_counts[tag] - close_counts[tag]
    if diff != 0:
        print(f"  IMBALANCE: <{tag}> has {open_counts[tag]} opens vs {close_counts[tag]} closes (diff={diff:+d})")
        imbalance = True

if not imbalance:
    print("  All tags balanced. OK")

# ─── 3. CODE BLOCKS ───────────────────────────────────────
print()
print("--- Code Blocks ---")
code_opens = len(re.findall(r'<pre class="code-block"><code', html))
code_closes = len(re.findall(r"</code></pre>", html))
if code_opens != code_closes:
    print(f"  IMBALANCE: {code_opens} open vs {code_closes} closed")
else:
    print(f"  {code_opens} code blocks, all balanced. OK")

# ─── 4. STRAY AMPERSANDS ──────────────────────────────────
print()
print("--- Stray Ampersands ---")
stray = 0
valid_entities = ["amp;", "lt;", "gt;", "quot;", "#38;", "#60;", "#62;",
                  "#8211;", "#8212;", "#8220;", "#8221;", "#8230;", "apos;"]
for i, ch in enumerate(html):
    if ch == "&":
        next_5 = html[i+1:i+6].lower()
        if not any(next_5.startswith(v) for v in valid_entities):
            context = html[max(0,i-15):i+20].replace("\n", " ").strip()
            if stray < 10:
                print(f"  Stray &: ...{context}...")
            stray += 1
if stray == 0:
    print("  No stray ampersands. OK")
else:
    print(f"  Total stray &: {stray} (may be in URLs/CSS - harmless)")

# ─── 5. SECTION OVERVIEW ──────────────────────────────────
print()
print("--- All Sections ---")
sections = re.findall(r"<h2 id='([^']+)'>([^<]+)</h2>", html)
for sid, stitle in sections:
    print(f"  [{sid}] {stitle}")
print(f"  Total: {len(sections)} sections")

# ─── 6. FILE STATS ────────────────────────────────────────
print()
print("--- File Stats ---")
print(f"  Size: {len(html):,} bytes")
print(f"  Lines: {html.count(chr(10)):,}")

print()
print("=" * 60)
print("AUDIT COMPLETE")
print("=" * 60)
