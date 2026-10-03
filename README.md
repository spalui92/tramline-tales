# Tramline Tales

Old tracks, new thoughts. A notebook that rattles through the city of brands, stopping wherever the ink finds a story.

Live at https://spalui92.github.io/tramline-tales

## Add a new article

1. Create a new file in the `articles/` folder. Name it after the publishing date, for example `2026-10-18.md`. (Two articles on one day: `2026-10-18-b.md`.)
2. Start the file with this header, then write the article underneath:

```
---
title: The title of the article
date: 2026-10-18
tag: marketing · craft
note: see p.1
summary: One or two lines for Google and link previews (optional).
---

First paragraph. Leave an empty line between paragraphs.

## A subheading

More text.
```

Only `title` and `date` are required. `tag` is the small red label above the date, `note` is a handwritten scribble in the margin, and `summary` is used for search results and shared links (if left out, the first lines of the article are used).

3. Commit the file. GitHub rebuilds and republishes the site on its own in about a minute.

Long articles flow onto extra pages automatically. Every article starts on a left-hand page.

## Change the diary's name, days or details

Edit `config.json`: `name`, `author`, `initials`, `place`, `stampPlace`, `start`, `days` (publishing days), `motto` and `description`.

Once the site has its address, put it in `siteUrl` (for example `https://spalui92.github.io/tramline-tales`). That switches on the sitemap and makes every "copy link to this entry" and preview image point to the real address.

## Build it yourself (optional)

```
python3 build.py
```

The finished site appears in `_site/`.

## One-time GitHub setup

In the repository: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
