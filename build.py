#!/usr/bin/env python3
"""Build the diary site.

Reads config.json and every article in articles/*.md, then writes the
finished site into _site/:

  _site/index.html      the flip-book diary (all articles baked in)
  _site/e/<slug>.html   one small page per article, for search engines and
                        link previews; real visitors are sent straight to
                        that article's page in the diary
  _site/sitemap.xml     only when siteUrl is set in config.json
  _site/robots.txt
  _site/og-cover.png    the preview image shown when a link is shared

Usage:  python3 build.py            (no extra packages needed)
        python3 build.py --preview  also writes _preview.html for previews
"""
import datetime
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def image_size(path):
    """Width and height of a JPEG or PNG, without extra packages."""
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
            i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    sys.exit(f"{path.name}: use a .jpg or .png image")


def read_article(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    meta, body = {}, text
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip().lower()] = val.strip()
        body = m.group(2)
    for need in ("title", "date"):
        if not meta.get(need):
            sys.exit(f"{path.name}: missing '{need}:' at the top of the file")
    try:
        datetime.date.fromisoformat(meta["date"])
    except ValueError:
        sys.exit(f"{path.name}: date must look like 2026-10-04")
    blocks = []
    for chunk in re.split(r"\n\s*\n", body.strip()):
        chunk = " ".join(chunk.split())
        if not chunk:
            continue
        img = re.fullmatch(r"!\[(.*?)\]\((.+?)\)", chunk)
        if img:
            src = img.group(2).strip()
            file = ROOT / src
            if not file.exists():
                sys.exit(f"{path.name}: picture not found: {src}")
            w, h = image_size(file)
            blocks.append({"t": "img", "x": img.group(1).strip(), "src": src, "w": w, "h": h})
        elif chunk.startswith("## "):
            blocks.append({"t": "h", "x": chunk[3:].strip()})
        else:
            blocks.append({"t": "p", "x": chunk})
    if not any(b["t"] == "p" for b in blocks):
        sys.exit(f"{path.name}: the article has no text")
    summary = meta.get("summary") or next((b["x"] for b in blocks if b["t"] == "p"), "")
    if len(summary) > 160:
        summary = summary[:157].rsplit(" ", 1)[0] + "..."
    return {
        "slug": path.stem,
        "title": meta["title"],
        "date": meta["date"],
        "tag": meta.get("tag", ""),
        "note": meta.get("note", ""),
        "summary": summary,
        "image": next((b["src"] for b in blocks if b["t"] == "img"), ""),
        "body": blocks,
    }


def long_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.strftime('%A')}, {d.day} {MONTHS[d.month - 1]} {d.year}"


def esc(s):
    return html.escape(str(s), quote=True)


def abs_url(cfg, path):
    base = cfg.get("siteUrl", "").rstrip("/")
    return f"{base}/{path}" if base else path


def archive_html(cfg, entries):
    """Plain copy of every article: read by search engines and screen readers."""
    out = [f'<section id="archive" class="sr" aria-label="All entries in {esc(cfg["name"])}">',
           f'<h1>{esc(cfg["name"])} by {esc(cfg["author"])}</h1>',
           f'<p>{esc(cfg["description"])}</p>']
    for e in entries:
        out.append(f'<article id="a-{esc(e["slug"])}"><h2>{esc(e["title"])}</h2>'
                   f'<p><time datetime="{e["date"]}">{long_date(e["date"])}</time></p>')
        for b in e["body"]:
            out.append(block_html(b, "", 3))
        out.append(f'<p><a href="e/{esc(e["slug"])}.html">Link to this entry</a></p></article>')
    out.append("</section>")
    return "\n".join(out)


def block_html(b, prefix, level):
    if b["t"] == "h":
        return f'<h{level}>{esc(b["x"])}</h{level}>'
    if b["t"] == "img":
        return (f'<figure><img src="{esc(prefix + b["src"])}" alt="{esc(b["x"])}" '
                f'width="{b["w"]}" height="{b["h"]}" loading="lazy"><figcaption>{esc(b["x"])}</figcaption></figure>')
    return f'<p>{esc(b["x"])}</p>'


def index_meta(cfg, entries):
    image = abs_url(cfg, "og-cover.png")
    tags = [
        f'<meta name="description" content="{esc(cfg["description"])}">',
        f'<meta name="author" content="{esc(cfg["author"])}">',
        f'<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{esc(cfg["name"])}">',
        f'<meta property="og:title" content="{esc(cfg["name"])} · {esc(cfg["author"])}">',
        f'<meta property="og:description" content="{esc(cfg["description"])}">',
        f'<meta property="og:image" content="{esc(image)}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    if cfg.get("siteUrl"):
        tags.append(f'<link rel="canonical" href="{esc(abs_url(cfg, ""))}">')
        tags.append(f'<meta property="og:url" content="{esc(abs_url(cfg, ""))}">')
    ld = {
        "@context": "https://schema.org", "@type": "Blog",
        "name": cfg["name"], "description": cfg["description"],
        "author": {"@type": "Person", "name": cfg["author"]},
        "blogPost": [{
            "@type": "BlogPosting", "headline": e["title"], "datePublished": e["date"],
            "description": e["summary"], "url": abs_url(cfg, f"e/{e['slug']}.html"),
            "author": {"@type": "Person", "name": cfg["author"]},
        } for e in entries],
    }
    tags.append('<script type="application/ld+json">' +
                json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    return "\n".join(tags)


def entry_page(cfg, e):
    page_url = abs_url(cfg, f"e/{e['slug']}.html")
    diary = f"../#{e['slug']}"
    pic = e["image"] or "og-cover.png"
    image = abs_url(cfg, pic) if cfg.get("siteUrl") else "../" + pic
    body = "\n".join(block_html(b, "../", 2) for b in e["body"])
    canonical = f'<link rel="canonical" href="{esc(page_url)}">' if cfg.get("siteUrl") else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(e["title"])} · {esc(cfg["name"])}</title>
<meta name="description" content="{esc(e["summary"])}">
<meta name="author" content="{esc(cfg["author"])}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{esc(cfg["name"])}">
<meta property="og:title" content="{esc(e["title"])}">
<meta property="og:description" content="{esc(e["summary"])}">
<meta property="og:image" content="{esc(image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="article:published_time" content="{e["date"]}">
<meta property="article:author" content="{esc(cfg["author"])}">
<meta name="twitter:card" content="summary_large_image">
{canonical}
<script>location.replace({json.dumps(diary)});</script>
<style>
body{{margin:0;background:#9a693b;font-family:"Courier Prime","Courier New",monospace;color:#2b2724;padding:24px 16px}}
img{{max-width:100%;height:auto}}figure{{margin:2rem 0}}figcaption{{font-style:italic;color:#6b6155}}
main{{max-width:40rem;margin:0 auto;background:#efdfbb;padding:32px 28px;line-height:1.8;box-shadow:0 10px 30px rgba(0,0,0,.35)}}
h1,h2{{color:#1f3a68;font-weight:400;text-wrap:balance}}
a{{color:#1f3a68}}
</style>
</head>
<body>
<main>
<p><a href="{esc(diary)}">Open this entry in {esc(cfg["name"])}</a></p>
<h1>{esc(e["title"])}</h1>
<p><time datetime="{e["date"]}">{long_date(e["date"])}</time> · {esc(cfg["author"])}</p>
{body}
</main>
</body>
</html>
"""


def main():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    entries = [read_article(p) for p in sorted((ROOT / "articles").glob("*.md"))]
    entries.sort(key=lambda e: (e["date"], e["slug"]))
    slugs = [e["slug"] for e in entries]
    if len(set(slugs)) != len(slugs):
        sys.exit("two articles share a file name")

    data = {"config": {k: cfg[k] for k in ("name", "author", "initials", "place", "stampPlace",
                                             "start", "days", "motto", "siteUrl")},
            "entries": [{k: e[k] for k in ("slug", "title", "date", "tag", "note", "body")}
                        for e in entries]}
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    page = (tpl.replace("{{TITLE}}", esc(cfg["name"]))
               .replace("{{META}}", index_meta(cfg, entries))
               .replace("{{DATA}}", data_json)
               .replace("{{ARCHIVE}}", archive_html(cfg, entries)))

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "e").mkdir(parents=True)
    head = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
    (OUT / "index.html").write_text(head + page, encoding="utf-8")
    for e in entries:
        (OUT / "e" / f"{e['slug']}.html").write_text(entry_page(cfg, e), encoding="utf-8")
    if (ROOT / "images").is_dir():
        shutil.copytree(ROOT / "images", OUT / "images")
    if (ROOT / "og-cover.png").exists():
        shutil.copy(ROOT / "og-cover.png", OUT / "og-cover.png")
    (OUT / ".nojekyll").write_text("")

    robots = "User-agent: *\nAllow: /\n"
    if cfg.get("siteUrl"):
        urls = [abs_url(cfg, "")] + [abs_url(cfg, f"e/{e['slug']}.html") for e in entries]
        dates = [entries[-1]["date"] if entries else cfg["start"]] + [e["date"] for e in entries]
        sm = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        sm += [f"  <url><loc>{esc(u)}</loc><lastmod>{d}</lastmod></url>" for u, d in zip(urls, dates)]
        sm.append("</urlset>")
        (OUT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
        robots += f"Sitemap: {abs_url(cfg, 'sitemap.xml')}\n"
    (OUT / "robots.txt").write_text(robots, encoding="utf-8")

    if "--preview" in sys.argv:
        (ROOT / "_preview.html").write_text(page, encoding="utf-8")

    print(f"Built {len(entries)} entries into {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
